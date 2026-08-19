from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import BaseModel
from parts.models import Part
import uuid


class InspectionPlan(BaseModel):
    """检验计划"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('PENDING_REVIEW', '待审核'),
        ('ACTIVE', '激活'),
        ('IN_PROGRESS', '执行中'),
        ('COMPLETED', '已完成'),
        ('ARCHIVED', '已归档'),
    ]
    
    STANDARD_CHOICES = [
        ('AS9102', 'AS9102航空航天'),
        ('PPAP', 'PPAP生产件批准'),
        ('FAI', '首件检验'),
        ('CUSTOM', '自定义'),
    ]
    
    plan_number = models.CharField(max_length=100, unique=True, verbose_name='计划编号')
    plan_name = models.CharField(max_length=200, verbose_name='计划名称')
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='inspection_plans', verbose_name='零件'
    )
    standard = models.CharField(
        max_length=20, choices=STANDARD_CHOICES,
        default='AS9102', verbose_name='标准类型'
    )
    
    # 检验信息
    sample_size = models.PositiveIntegerField(default=1, verbose_name='样本数量')
    description = models.TextField(blank=True, verbose_name='计划描述')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name='状态'
    )
    
    # 审批信息
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_plans',
        verbose_name='批准人'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='批准时间')
    
    class Meta:
        db_table = 'inspection_plans'
        verbose_name = '检验计划'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.plan_number} - {self.plan_name}"
    
    def save(self, *args, **kwargs):
        if not self.plan_number:
            # 自动生成计划编号
            prefix = 'FAI' if self.standard == 'FAI' else 'PLAN'
            date_str = timezone.now().strftime('%Y%m%d')
            count = InspectionPlan.objects.filter(
                plan_number__startswith=f'{prefix}-{date_str}'
            ).count()
            self.plan_number = f'{prefix}-{date_str}-{count+1:04d}'
        super().save(*args, **kwargs)

    @property
    def characteristic_accountability(self):
        """
        AS9102要求图纸上100%的特性都需被ballooned并形成检验记录（特性完整性核对）。
        对比"零件最新一次CAD/图纸解析出的尺寸总数"与"本计划已建立的检验特性数"，
        覆盖不足时应在报告中提示，而不是静默视为完整。
        """
        from parts.models import CADExtraction
        latest_extraction = CADExtraction.objects.filter(
            part=self.part, status='COMPLETED'
        ).order_by('-created_at').first()

        if not latest_extraction:
            return None

        total_dimensions = latest_extraction.dimensions.count()
        covered = self.characteristics.count()

        return {
            'total_dimensions': total_dimensions,
            'covered_characteristics': covered,
            'is_complete': covered >= total_dimensions if total_dimensions > 0 else None,
            'coverage_pct': round(covered / total_dimensions * 100, 1) if total_dimensions > 0 else None,
            'extraction_reviewed': latest_extraction.reviewed,
        }


class CharacteristicCategory(models.Model):
    """特性分类"""
    CATEGORY_CHOICES = [
        ('DIMENSION', '尺寸特性'),
        ('PROCESS', '工艺特性'),
        ('MATERIAL', '材料特性'),
        ('ASSEMBLY', '装配特性'),
        ('APPEARANCE', '外观特性'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='分类名称')
    code = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True, verbose_name='分类代码')
    description = models.TextField(blank=True, verbose_name='描述')
    
    class Meta:
        db_table = 'characteristic_categories'
        verbose_name = '特性分类'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name


class InspectionCharacteristic(models.Model):
    """检验特性"""
    CHAR_TYPE_CHOICES = [
        ('DIMENSION', '尺寸'),
        ('ANGULAR', '角度'),
        ('GD_T', '形位公差'),
        ('SURFACE', '表面粗糙度'),
        ('HARDNESS', '硬度'),
        ('OTHER', '其他'),
    ]
    
    MEASUREMENT_METHOD_CHOICES = [
        ('CMM', '三坐标测量'),
        ('OPTICAL', '光学测量'),
        ('MECHANICAL', '机械测量'),
        ('VISUAL', '目视检查'),
        ('LASER', '激光扫描'),
        ('OTHER', '其他'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(
        InspectionPlan, on_delete=models.CASCADE,
        related_name='characteristics', verbose_name='检验计划'
    )
    
    # 特性信息
    char_number = models.CharField(max_length=50, verbose_name='特性编号')
    char_name = models.CharField(max_length=200, verbose_name='特性名称')
    char_type = models.CharField(
        max_length=20, choices=CHAR_TYPE_CHOICES,
        verbose_name='特性类型'
    )
    category = models.ForeignKey(
        CharacteristicCategory, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='特性分类'
    )
    
    # 公差信息
    nominal_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='理论值'
    )
    upper_tolerance = models.DecimalField(
        max_digits=10, decimal_places=6,
        default=0, null=True, blank=True, verbose_name='上公差',
        help_text='留空表示无上限（如平面度、位置度等单侧形位公差）'
    )
    lower_tolerance = models.DecimalField(
        max_digits=10, decimal_places=6,
        default=0, null=True, blank=True, verbose_name='下公差',
        help_text='留空表示无下限'
    )
    unit = models.CharField(max_length=10, default='mm', verbose_name='单位')
    
    # 测量信息
    measurement_method = models.CharField(
        max_length=20, choices=MEASUREMENT_METHOD_CHOICES,
        default='CMM', verbose_name='测量方法'
    )
    gage_id = models.CharField(max_length=50, blank=True, verbose_name='量具编号')
    gage_name = models.CharField(max_length=100, blank=True, verbose_name='量具名称')
    
    # 关键特性
    is_critical = models.BooleanField(default=False, verbose_name='关键特性')
    is_key_characteristic = models.BooleanField(default=False, verbose_name='关键特性(KC)')
    
    # 序号
    sequence = models.PositiveIntegerField(default=1, verbose_name='序号')
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    drawing_reference = models.CharField(max_length=100, blank=True, verbose_name='图纸参考')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'inspection_characteristics'
        verbose_name = '检验特性'
        verbose_name_plural = verbose_name
        ordering = ['sequence', 'char_number']
        unique_together = ['plan', 'char_number']
    
    def __str__(self):
        return f"{self.char_number} - {self.char_name}"
    
    @property
    def upper_limit(self):
        """上限（无上公差时返回None，表示该特性无上限约束）"""
        if self.upper_tolerance is None:
            return None
        return self.nominal_value + self.upper_tolerance

    @property
    def lower_limit(self):
        """下限（无下公差时返回None，表示该特性无下限约束）"""
        if self.lower_tolerance is None:
            return None
        return self.nominal_value + self.lower_tolerance

    @property
    def tolerance_band(self):
        """公差带（单侧公差无法构成完整公差带，返回None）"""
        if self.upper_tolerance is None or self.lower_tolerance is None:
            return None
        return self.upper_tolerance - self.lower_tolerance
