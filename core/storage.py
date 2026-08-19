"""
厂商无关的对象存储后端 - 用于Django文件上传

基于boto3的S3协议实现，兼容AWS S3、阿里云OSS、腾讯云COS、火山引擎TOS等
S3兼容对象存储服务。具体厂商、密钥、桶名等均可在「系统管理 > 引擎配置」页面
后台配置，无需修改代码或重新部署。

未配置对象存储时，自动降级为本地文件系统存储（FileSystemStorage），
保证开发环境/未配置存储的环境也能正常运行。

注意：存储配置变更后需要重启应用进程才能生效（Django的default_storage在
进程内是单例，首次访问时才会读取当前配置并固定下来）。
"""
import os
import re
import logging
import unicodedata
from django.core.files.storage import Storage, FileSystemStorage
from django.core.files.base import File
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


# 常见厂商的S3兼容端点预设。region留空时无法自动拼出endpoint，需用户在后台手填。
STORAGE_PROVIDER_PRESETS = {
    's3': {
        'label': 'AWS S3 / 标准S3兼容存储',
        'endpoint_template': '',  # AWS官方SDK可不传endpoint，由region自动推断
        'addressing_style': 'virtual',
    },
    'aliyun_oss': {
        'label': '阿里云OSS',
        'endpoint_template': 'https://oss-{region}.aliyuncs.com',
        'addressing_style': 'virtual',
    },
    'tencent_cos': {
        'label': '腾讯云COS',
        'endpoint_template': 'https://cos.{region}.myqcloud.com',
        'addressing_style': 'virtual',
    },
    'volcengine_tos': {
        'label': '火山引擎TOS',
        'endpoint_template': 'https://tos-s3-{region}.volces.com',
        'addressing_style': 'virtual',
    },
}


def _get_config_value(env_key: str, db_key: str, default: str = '') -> str:
    """配置读取：环境变量优先，其次数据库SystemConfig"""
    value = os.environ.get(env_key)
    if value:
        return value
    try:
        from core.models import SystemConfig
        value = SystemConfig.get_value(db_key)
    except Exception:
        value = None
    return value or default


def get_storage_config() -> dict:
    """读取当前生效的对象存储配置"""
    provider = _get_config_value('STORAGE_PROVIDER', 'storage_provider', '')
    access_key = _get_config_value('STORAGE_ACCESS_KEY_ID', 'storage_access_key_id', '')
    secret_key = _get_config_value('STORAGE_ACCESS_KEY_SECRET', 'storage_access_key_secret', '')
    bucket = _get_config_value('STORAGE_BUCKET_NAME', 'storage_bucket_name', '')
    endpoint_url = _get_config_value('STORAGE_ENDPOINT_URL', 'storage_endpoint_url', '')
    region = _get_config_value('STORAGE_REGION', 'storage_region', '')
    public_base_url = _get_config_value('STORAGE_PUBLIC_BASE_URL', 'storage_public_base_url', '')
    addressing_style = _get_config_value('STORAGE_ADDRESSING_STYLE', 'storage_addressing_style', '')

    preset = STORAGE_PROVIDER_PRESETS.get(provider, {})
    if not endpoint_url and preset.get('endpoint_template') and region:
        endpoint_url = preset['endpoint_template'].format(region=region)
    if not addressing_style:
        addressing_style = preset.get('addressing_style', 'virtual')

    return {
        'provider': provider,
        'provider_label': preset.get('label', provider),
        'access_key': access_key,
        'secret_key': secret_key,
        'bucket': bucket,
        'endpoint_url': endpoint_url,
        'region': region or 'us-east-1',
        'public_base_url': public_base_url.rstrip('/') if public_base_url else '',
        'addressing_style': addressing_style,
    }


def is_object_storage_configured() -> bool:
    """是否已具备使用对象存储的最低条件（厂商+密钥+桶名）"""
    cfg = get_storage_config()
    return bool(cfg['provider'] and cfg['access_key'] and cfg['secret_key'] and cfg['bucket'])


def _sanitize_file_name(name: str) -> str:
    """清理文件名：去除危险字符，保留可读性"""
    name = name.replace('\\', '/').lstrip('/')
    name = unicodedata.normalize('NFKC', name)
    name = re.sub(r'[\x00-\x1f]', '', name)
    return name


@deconstructible
class S3CompatibleStorage(Storage):
    """S3协议对象存储后端，兼容AWS S3/阿里云OSS/腾讯云COS/火山引擎TOS"""

    def __init__(self):
        import boto3
        from botocore.config import Config as BotoConfig

        cfg = get_storage_config()
        if not is_object_storage_configured():
            raise ValueError("对象存储未配置完整（缺少 provider/access_key/secret_key/bucket）")

        self._cfg = cfg
        self._bucket = cfg['bucket']

        boto_config = BotoConfig(
            s3={'addressing_style': cfg['addressing_style']},
            signature_version='s3v4',
        )
        self._client = boto3.client(
            's3',
            aws_access_key_id=cfg['access_key'],
            aws_secret_access_key=cfg['secret_key'],
            endpoint_url=cfg['endpoint_url'] or None,
            region_name=cfg['region'],
            config=boto_config,
        )
        logger.info(
            f"S3CompatibleStorage初始化: provider={cfg['provider']} "
            f"bucket={self._bucket} endpoint={cfg['endpoint_url']}"
        )

    def get_available_name(self, name, max_length=None):
        return _sanitize_file_name(name)

    def generate_filename(self, name):
        return _sanitize_file_name(name)

    def _open(self, name, mode='rb'):
        import io
        obj = self._client.get_object(Bucket=self._bucket, Key=name)
        return File(io.BytesIO(obj['Body'].read()), name=name)

    def _save(self, name, content):
        import mimetypes
        content_type = getattr(content, 'content_type', None)
        if not content_type:
            content_type, _ = mimetypes.guess_type(name)
        content.seek(0)
        extra_args = {'ContentType': content_type} if content_type else {}
        self._client.upload_fileobj(content, self._bucket, name, ExtraArgs=extra_args)
        return name

    def exists(self, name):
        from botocore.exceptions import ClientError
        try:
            self._client.head_object(Bucket=self._bucket, Key=name)
            return True
        except ClientError:
            return False

    def delete(self, name):
        self._client.delete_object(Bucket=self._bucket, Key=name)

    def size(self, name):
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=name)
            return resp.get('ContentLength', 0)
        except Exception as e:
            logger.warning(f"获取文件大小失败: {name}, 错误: {e}")
            return 0

    def url(self, name):
        if self._cfg['public_base_url']:
            return f"{self._cfg['public_base_url']}/{name}"
        # 桶为私有时，生成1小时有效的预签名URL
        return self._client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self._bucket, 'Key': name},
            ExpiresIn=3600,
        )

    def listdir(self, path):
        prefix = (path.rstrip('/') + '/') if path else ''
        resp = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix, Delimiter='/')
        dirs = [p['Prefix'][len(prefix):].rstrip('/') for p in resp.get('CommonPrefixes', [])]
        files = [c['Key'][len(prefix):] for c in resp.get('Contents', []) if c['Key'] != prefix]
        return dirs, files

    def path(self, name):
        raise NotImplementedError("对象存储不支持本地文件路径")

    def get_accessed_time(self, name):
        return None

    def get_created_time(self, name):
        return None

    def get_modified_time(self, name):
        return None


@deconstructible
class S3Storage(Storage):
    """
    统一存储入口：进程启动后首次使用时，根据后台「引擎配置」中的存储设置
    自动选择对象存储(S3/OSS/COS/TOS)或本地文件系统存储，并将后续所有方法
    委托给所选后端。

    保留 `S3Storage` 这个类名（settings.py中 STORAGES['default']['BACKEND']
    引用此类）以避免每次更换存储厂商都要改settings.py。
    """

    def __init__(self):
        if is_object_storage_configured():
            self._backend = S3CompatibleStorage()
        else:
            from django.conf import settings
            media_root = getattr(settings, 'MEDIA_ROOT', None) or str(settings.BASE_DIR / 'media')
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            self._backend = FileSystemStorage(location=media_root, base_url=media_url)
            logger.info("对象存储未配置，使用本地文件系统存储")

    def get_available_name(self, name, max_length=None):
        return self._backend.get_available_name(name, max_length=max_length)

    def generate_filename(self, name):
        return self._backend.generate_filename(name)

    def _open(self, name, mode='rb'):
        return self._backend._open(name, mode)

    def _save(self, name, content):
        return self._backend._save(name, content)

    def exists(self, name):
        return self._backend.exists(name)

    def delete(self, name):
        return self._backend.delete(name)

    def size(self, name):
        return self._backend.size(name)

    def url(self, name):
        return self._backend.url(name)

    def listdir(self, path):
        return self._backend.listdir(path)

    def path(self, name):
        return self._backend.path(name)

    def get_accessed_time(self, name):
        return self._backend.get_accessed_time(name)

    def get_created_time(self, name):
        return self._backend.get_created_time(name)

    def get_modified_time(self, name):
        return self._backend.get_modified_time(name)
