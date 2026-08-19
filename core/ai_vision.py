"""
厂商无关的AI视觉模型客户端

支持任何提供OpenAI兼容多模态(vision)接口的厂商，预置常见中国厂商默认端点：
- doubao  豆包（火山引擎方舟）
- kimi    Kimi（月之暗面 Moonshot AI）
- glm     GLM（智谱AI）
- custom  自定义OpenAI兼容接口（私有部署/其他厂商）

配置来源优先级：环境变量 > 数据库 SystemConfig（后台"引擎配置"页面可配置）。
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


PROVIDER_PRESETS = {
    'doubao': {
        'label': '豆包（火山引擎方舟）',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'default_model': 'doubao-seed-1-6-vision-250815',
    },
    'kimi': {
        'label': 'Kimi（月之暗面）',
        'base_url': 'https://api.moonshot.cn/v1',
        'default_model': 'moonshot-v1-128k-vision-preview',
    },
    'glm': {
        'label': 'GLM（智谱AI）',
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'default_model': 'glm-4v-plus',
    },
    'custom': {
        'label': '自定义(OpenAI兼容接口)',
        'base_url': '',
        'default_model': '',
    },
}


class AIVisionConfigError(ValueError):
    """AI视觉模型未正确配置"""
    pass


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


def get_ai_vision_config() -> dict:
    """读取当前生效的AI视觉模型配置"""
    provider = _get_config_value('AI_VISION_PROVIDER', 'ai_vision_provider', '')
    api_key = _get_config_value('AI_VISION_API_KEY', 'ai_vision_api_key', '')
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS['custom'])
    base_url = _get_config_value('AI_VISION_BASE_URL', 'ai_vision_base_url', '') or preset['base_url']
    model = _get_config_value('AI_VISION_MODEL', 'ai_vision_model', '') or preset['default_model']

    return {
        'provider': provider,
        'provider_label': preset['label'] if provider else '',
        'api_key': api_key,
        'base_url': base_url,
        'model': model,
        'key_source': 'env' if os.environ.get('AI_VISION_API_KEY') else ('database' if api_key else None),
    }


def is_ai_vision_configured() -> bool:
    """是否已具备调用云端AI视觉模型的最低条件（厂商+密钥+服务地址）"""
    cfg = get_ai_vision_config()
    return bool(cfg['api_key'] and cfg['base_url'])


class AIVisionClient:
    """
    轻量包装器：内部按需创建 langchain_openai.ChatOpenAI 实例（同一进程内按model+temperature缓存复用）。
    """

    def __init__(self):
        cfg = get_ai_vision_config()
        if not cfg['api_key']:
            raise AIVisionConfigError(
                "未配置AI视觉模型API密钥。\n"
                "请选择以下方式之一：\n"
                "1. 安装本地OCR引擎: pip install paddleocr paddlepaddle\n"
                "2. 在「系统管理 > 引擎配置」页面配置AI视觉模型（支持豆包/Kimi/GLM/自定义）\n"
                "3. 或设置环境变量 AI_VISION_PROVIDER / AI_VISION_API_KEY / AI_VISION_BASE_URL"
            )
        if not cfg['base_url']:
            raise AIVisionConfigError(
                f"AI视觉模型厂商「{cfg['provider'] or '未选择'}」缺少服务地址(base_url)配置，"
                "请在「系统管理 > 引擎配置」页面补充，或选择预置厂商（豆包/Kimi/GLM）自动填充"
            )
        self._cfg = cfg
        self._instances = {}

    def invoke(self, messages, model: Optional[str] = None, temperature: Optional[float] = None):
        from langchain_openai import ChatOpenAI

        model_name = model or self._cfg['model']
        if not model_name:
            raise AIVisionConfigError(
                f"AI视觉模型厂商「{self._cfg['provider']}」未指定模型名称，请在引擎配置页面填写"
            )
        temp = 0.1 if temperature is None else temperature
        cache_key = (model_name, temp)

        if cache_key not in self._instances:
            self._instances[cache_key] = ChatOpenAI(
                api_key=self._cfg['api_key'],
                base_url=self._cfg['base_url'],
                model=model_name,
                temperature=temp,
            )
        return self._instances[cache_key].invoke(messages)


def get_ai_vision_client() -> AIVisionClient:
    """获取AI视觉模型客户端实例（未配置时抛出AIVisionConfigError）"""
    return AIVisionClient()
