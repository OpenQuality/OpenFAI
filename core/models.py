from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    """基础模型，包含通用字段"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, 
        related_name='%(class)s_created', verbose_name='创建人'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='%(class)s_updated', verbose_name='更新人'
    )
    
    class Meta:
        abstract = True


class FAIProject(BaseModel):
    """FAI项目管理"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('IN_PROGRESS', '进行中'),
        ('PENDING_REVIEW', '待审核'),
        ('COMPLETED', '已完成'),
        ('ARCHIVED', '已归档'),
    ]
    
    project_number = models.CharField(max_length=100, unique=True, verbose_name='项目编号')
    project_name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    
    # 关联零件
    part = models.ForeignKey(
        'parts.Part', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects',
        verbose_name='关联零件'
    )
    
    # 关联检验计划
    inspection_plan = models.ForeignKey(
        'inspections.InspectionPlan', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects',
        verbose_name='关联检验计划'
    )
    
    # 关联测量批次
    measurement_batch = models.ForeignKey(
        'measurements.MeasurementBatch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects',
        verbose_name='关联测量批次'
    )
    
    # 关联检验报告
    inspection_report = models.ForeignKey(
        'reports.InspectionReport', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects',
        verbose_name='关联检验报告'
    )
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name='状态'
    )
    
    # 进度信息
    progress_percentage = models.PositiveIntegerField(default=0, verbose_name='完成进度')
    
    # 日期信息
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    target_date = models.DateField(null=True, blank=True, verbose_name='目标日期')
    completed_date = models.DateField(null=True, blank=True, verbose_name='完成日期')
    
    class Meta:
        db_table = 'fai_projects'
        verbose_name = 'FAI项目'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.project_number} - {self.project_name}"
    
    def update_progress(self):
        """更新项目进度百分比和状态"""
        steps = self.steps.all()
        total_steps = steps.count()
        if total_steps == 0:
            return
        
        completed_steps = steps.filter(status='COMPLETED').count()
        self.progress_percentage = int((completed_steps / total_steps) * 100)
        
        # 根据步骤完成情况自动更新状态
        if self.progress_percentage == 100:
            # 所有步骤完成
            self.status = 'COMPLETED'
            self.completed_date = timezone.now().date()
        elif self.progress_percentage > 0:
            # 有步骤在进行中
            if self.status == 'DRAFT':
                self.status = 'IN_PROGRESS'
        
        self.save(update_fields=['progress_percentage', 'status', 'completed_date'])
        
    def get_step_progress(self):
        """获取步骤进度详情"""
        steps = self.steps.all().order_by('step_order')
        total = steps.count()
        completed = steps.filter(status='COMPLETED').count()
        in_progress = steps.filter(status='IN_PROGRESS').count()
        pending = steps.filter(status='PENDING').count()
        
        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'percentage': int((completed / total) * 100) if total > 0 else 0
        }
    
    def save(self, *args, **kwargs):
        if not self.project_number:
            date_str = timezone.now().strftime('%Y%m%d')
            count = FAIProject.objects.filter(
                project_number__startswith=f'PRJ-{date_str}'
            ).count()
            self.project_number = f'PRJ-{date_str}-{count+1:04d}'
        super().save(*args, **kwargs)


class ProjectStep(models.Model):
    """项目步骤"""
    STEP_CHOICES = [
        ('PRODUCT_INFO', '产品信息'),
        ('DRAWING_IMPORT', '图纸导入'),
        ('OCR_RECOGNITION', 'OCR识别'),
        ('DIMENSION_TABLE', '尺寸公差表'),
        ('MEASUREMENT', '测量数据'),
        ('ANALYSIS', '统计分析'),
        ('REPORT', '报告生成'),
        ('APPROVAL', '审批流程'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('IN_PROGRESS', '进行中'),
        ('COMPLETED', '已完成'),
        ('SKIPPED', '已跳过'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        FAIProject, on_delete=models.CASCADE,
        related_name='steps', verbose_name='项目'
    )
    
    # 步骤信息
    step_code = models.CharField(
        max_length=30, choices=STEP_CHOICES,
        verbose_name='步骤代码'
    )
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    step_order = models.PositiveIntegerField(default=1, verbose_name='步骤顺序')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    
    # 完成信息
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='完成人'
    )
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'project_steps'
        verbose_name = '项目步骤'
        verbose_name_plural = verbose_name
        ordering = ['step_order']
        unique_together = ['project', 'step_code']
    
    def __str__(self):
        return f"{self.project.project_number} - {self.step_name}"


class SystemLog(models.Model):
    """系统操作日志"""
    ACTION_CHOICES = [
        ('CREATE', '创建'),
        ('UPDATE', '更新'),
        ('DELETE', '删除'),
        ('LOGIN', '登录'),
        ('LOGOUT', '登出'),
        ('APPROVE', '审批'),
        ('REJECT', '拒绝'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作用户')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='操作类型')
    model_name = models.CharField(max_length=100, verbose_name='模型名称')
    object_id = models.CharField(max_length=100, blank=True, verbose_name='对象ID')
    description = models.TextField(verbose_name='操作描述')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=255, blank=True, verbose_name='用户代理')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    
    class Meta:
        db_table = 'system_logs'
        verbose_name = '系统日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name}"


class SystemConfig(models.Model):
    """系统配置"""
    CONFIG_CATEGORIES = [
        ('ocr', 'OCR配置'),
        ('api', 'API配置'),
        ('storage', '存储配置'),
        ('email', '邮件配置'),
        ('system', '系统配置'),
    ]
    
    CONFIG_KEYS = [
        # OCR配置（本地引擎，无需密钥）
        ('ocr_default_engine', '默认OCR引擎', 'ocr'),
        # AI视觉模型配置（厂商无关，支持豆包/Kimi/GLM/自定义OpenAI兼容接口）
        ('ai_vision_provider', 'AI视觉模型厂商', 'ocr'),
        ('ai_vision_api_key', 'AI视觉模型API密钥', 'ocr'),
        ('ai_vision_base_url', 'AI视觉模型服务地址', 'ocr'),
        ('ai_vision_model', 'AI视觉模型名称', 'ocr'),
        # 百度OCR REST API（非LLM，专用文字识别服务）
        ('baidu_ocr_api_key', '百度OCR API Key', 'ocr'),
        ('baidu_ocr_secret_key', '百度OCR Secret Key', 'ocr'),
        # API配置
        ('api_base_url', 'API基础URL', 'api'),
        ('api_timeout', 'API超时时间(秒)', 'api'),
        # 存储配置（厂商无关，支持S3/阿里云OSS/腾讯云COS/火山引擎TOS）
        ('storage_provider', '存储服务厂商', 'storage'),
        ('storage_access_key_id', '存储AccessKey ID', 'storage'),
        ('storage_access_key_secret', '存储AccessKey Secret', 'storage'),
        ('storage_bucket_name', '存储桶名称', 'storage'),
        ('storage_endpoint_url', '存储服务地址(Endpoint)', 'storage'),
        ('storage_region', '存储区域(Region)', 'storage'),
        ('storage_public_base_url', '存储公开访问域名(可选,CDN/自定义域名)', 'storage'),
        ('storage_addressing_style', '存储寻址方式(path/virtual)', 'storage'),
        # 系统配置
        ('system_name', '系统名称', 'system'),
        ('company_name', '公司名称', 'system'),
    ]
    
    key = models.CharField(max_length=100, unique=True, verbose_name='配置键')
    value = models.TextField(blank=True, verbose_name='配置值')
    category = models.CharField(
        max_length=20, choices=CONFIG_CATEGORIES,
        default='system', verbose_name='分类'
    )
    description = models.CharField(max_length=255, blank=True, verbose_name='描述')
    is_secret = models.BooleanField(default=False, verbose_name='是否敏感')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'system_configs'
        verbose_name = '系统配置'
        verbose_name_plural = verbose_name
        ordering = ['category', 'key']
    
    def __str__(self):
        return f"{self.key} = {self.value[:50]}{'...' if len(self.value) > 50 else ''}"
    
    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值"""
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_value(cls, key, value, category='system', description='', is_secret=False):
        """设置配置值"""
        config, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'category': category,
                'description': description,
                'is_secret': is_secret
            }
        )
        return config
