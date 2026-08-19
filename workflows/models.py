from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from inspections.models import InspectionPlan
from reports.models import InspectionReport
from measurements.models import MeasurementRecord
from parts.models import Part
import uuid


class ApprovalWorkflow(models.Model):
    """审批工作流"""
    WORKFLOW_TYPE_CHOICES = [
        ('PLAN_APPROVAL', '检验计划审批'),
        ('REPORT_APPROVAL', '检验报告审批'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('IN_PROGRESS', '进行中'),
        ('COMPLETED', '已完成'),
        ('REJECTED', '已拒绝'),
        ('CANCELLED', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_type = models.CharField(
        max_length=50, choices=WORKFLOW_TYPE_CHOICES,
        verbose_name='工作流类型'
    )
    
    # 关联对象
    plan = models.ForeignKey(
        InspectionPlan, on_delete=models.CASCADE,
        null=True, blank=True, related_name='workflows',
        verbose_name='检验计划'
    )
    report = models.ForeignKey(
        InspectionReport, on_delete=models.CASCADE,
        null=True, blank=True, related_name='workflows',
        verbose_name='检验报告'
    )
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    current_step = models.PositiveIntegerField(default=1, verbose_name='当前步骤')
    
    # 发起人
    initiated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='initiated_workflows',
        verbose_name='发起人'
    )
    initiated_at = models.DateTimeField(auto_now_add=True, verbose_name='发起时间')
    
    # 完成时间
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    
    class Meta:
        db_table = 'approval_workflows'
        verbose_name = '审批工作流'
        verbose_name_plural = verbose_name
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"{self.get_workflow_type_display()} - {self.status}"
    
    @property
    def total_steps(self):
        """总步骤数"""
        return self.steps.count()
    
    @property
    def current_step_info(self):
        """当前步骤信息"""
        return self.steps.filter(step_number=self.current_step).first()


class ApprovalStep(models.Model):
    """审批步骤"""
    STEP_NAME_CHOICES = [
        ('SUBMIT', '提交'),
        ('REVIEW', '审核'),
        ('APPROVE', '批准'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('APPROVED', '已通过'),
        ('REJECTED', '已拒绝'),
        ('SKIPPED', '已跳过'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        ApprovalWorkflow, on_delete=models.CASCADE,
        related_name='steps', verbose_name='工作流'
    )
    
    # 步骤信息
    step_number = models.PositiveIntegerField(verbose_name='步骤序号')
    step_name = models.CharField(
        max_length=50, choices=STEP_NAME_CHOICES,
        verbose_name='步骤名称'
    )
    
    # 审批人
    approver = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='审批人'
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='分配时间')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    
    # 审批信息
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审批时间')
    comments = models.TextField(blank=True, verbose_name='审批意见')
    
    class Meta:
        db_table = 'approval_steps'
        verbose_name = '审批步骤'
        verbose_name_plural = verbose_name
        ordering = ['step_number']
        unique_together = ['workflow', 'step_number']
    
    def __str__(self):
        return f"{self.workflow} - Step {self.step_number}: {self.step_name}"


class ElectronicSignature(models.Model):
    """电子签名"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    step = models.OneToOneField(
        ApprovalStep, on_delete=models.CASCADE,
        related_name='signature', verbose_name='审批步骤'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        verbose_name='签名用户'
    )
    
    # 签名图片
    signature_image = models.ImageField(
        upload_to='signatures/', 
        blank=True, null=True, verbose_name='签名图片'
    )
    
    # 签名信息
    signed_at = models.DateTimeField(auto_now_add=True, verbose_name='签名时间')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=255, blank=True, verbose_name='用户代理')
    
    # 数字签名（用于验证）
    digital_hash = models.CharField(max_length=128, blank=True, verbose_name='数字哈希')
    
    class Meta:
        db_table = 'electronic_signatures'
        verbose_name = '电子签名'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.user.username} - {self.signed_at}"


class NonConformanceReport(models.Model):
    """不合格品报告"""
    PROBLEM_TYPE_CHOICES = [
        ('DIMENSION', '尺寸超差'),
        ('APPEARANCE', '外观缺陷'),
        ('MATERIAL', '材料问题'),
        ('PROCESS', '工艺问题'),
        ('ASSEMBLY', '装配问题'),
        ('OTHER', '其他'),
    ]
    
    SUPPLY_METHOD_CHOICES = [
        ('INTERNAL', '内部加工'),
        ('EXTERNAL', '外协加工'),
        ('PURCHASED', '外购件'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', '待处理'),
        ('IN_PROGRESS', '处理中'),
        ('PENDING_REVIEW', '待审核'),
        ('CLOSED', '已关闭'),
        ('CANCELLED', '已取消'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ncr_number = models.CharField(max_length=50, unique=True, verbose_name='NCR编号')
    
    # 关联零件
    part = models.ForeignKey(
        Part, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='non_conformances',
        verbose_name='零件'
    )
    
    # 关联测量记录
    measurement_record = models.ForeignKey(
        MeasurementRecord, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='non_conformances',
        verbose_name='测量记录'
    )
    
    # 产品信息
    product_name = models.CharField(max_length=200, verbose_name='品名')
    specification = models.CharField(max_length=200, blank=True, verbose_name='规格')
    batch_number = models.CharField(max_length=100, blank=True, verbose_name='批次号')
    department_code = models.CharField(max_length=50, blank=True, verbose_name='科号')
    
    # 问题信息
    problem_type = models.CharField(
        max_length=20, choices=PROBLEM_TYPE_CHOICES,
        verbose_name='问题类型'
    )
    problem_description = models.TextField(verbose_name='问题描述')
    defect_phenomenon = models.CharField(max_length=500, blank=True, verbose_name='不良现象')
    
    # 供应商/来源信息
    supply_method = models.CharField(
        max_length=20, choices=SUPPLY_METHOD_CHOICES,
        default='INTERNAL', verbose_name='供应方式'
    )
    supplier_name = models.CharField(max_length=200, blank=True, verbose_name='供方名称')
    delivery_date = models.DateField(null=True, blank=True, verbose_name='交货日期')
    
    # 处理信息
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='OPEN', verbose_name='状态'
    )
    responsible_person = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='responsible_ncrs',
        verbose_name='负责人'
    )
    
    # 检验信息
    inspector = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='inspected_ncrs',
        verbose_name='检验人'
    )
    inspected_at = models.DateTimeField(null=True, blank=True, verbose_name='检验时间')
    
    # 附件
    attachment = models.FileField(
        upload_to='ncr_attachments/',
        blank=True, null=True, verbose_name='附件'
    )
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'non_conformance_reports'
        verbose_name = '不合格品报告'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ncr_number} - {self.product_name}"
    
    def save(self, *args, **kwargs):
        if not self.ncr_number:
            # 自动生成NCR编号
            date_str = timezone.now().strftime('%Y%m%d')
            count = NonConformanceReport.objects.filter(
                ncr_number__startswith=f'NCR-{date_str}'
            ).count()
            self.ncr_number = f'NCR-{date_str}-{count+1:04d}'
        super().save(*args, **kwargs)


class NonConformanceAction(models.Model):
    """不合格品处理措施"""
    ACTION_TYPE_CHOICES = [
        ('REWORK', '返工'),
        ('REPAIR', '返修'),
        ('SCRAP', '报废'),
        ('CONCESSION', '让步接收'),
        ('RETURN', '退货'),
        ('REVIEW', '评审'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('IN_PROGRESS', '执行中'),
        ('COMPLETED', '已完成'),
        ('VERIFIED', '已验证'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ncr = models.ForeignKey(
        NonConformanceReport, on_delete=models.CASCADE,
        related_name='actions', verbose_name='不合格品报告'
    )
    
    # 措施信息
    action_type = models.CharField(
        max_length=20, choices=ACTION_TYPE_CHOICES,
        verbose_name='处理方式'
    )
    action_description = models.TextField(verbose_name='处理措施描述')
    
    # 责任人
    responsible_person = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='责任人'
    )
    due_date = models.DateField(null=True, blank=True, verbose_name='截止日期')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    
    # 完成信息
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    completion_notes = models.TextField(blank=True, verbose_name='完成备注')
    
    # 验证信息
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_actions',
        verbose_name='验证人'
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='验证时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'non_conformance_actions'
        verbose_name = '不合格品处理措施'
        verbose_name_plural = verbose_name
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.ncr.ncr_number} - {self.get_action_type_display()}"
