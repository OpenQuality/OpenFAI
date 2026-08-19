from django.db import models
from django.contrib.auth.models import User
from inspections.models import InspectionPlan
from measurements.models import MeasurementBatch
import uuid


def report_upload_path(instance, filename):
    """报告文件上传路径"""
    return f'reports/{instance.report_number}/{filename}'


class ReportTemplate(models.Model):
    """报告模板"""
    STANDARD_CHOICES = [
        ('AS9102', 'AS9102航空航天'),
        ('PPAP', 'PPAP生产件批准'),
        ('FAI', '首件检验'),
        ('CUSTOM', '自定义'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='模板名称')
    standard = models.CharField(
        max_length=20, choices=STANDARD_CHOICES,
        verbose_name='标准类型'
    )
    template_file = models.FileField(
        upload_to='templates/', 
        blank=True, null=True, verbose_name='模板文件'
    )
    description = models.TextField(blank=True, verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='创建人'
    )
    
    class Meta:
        db_table = 'report_templates'
        verbose_name = '报告模板'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name


class InspectionReport(models.Model):
    """检验报告"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('GENERATING', '生成中'),
        ('COMPLETED', '已完成'),
        ('PUBLISHED', '已发布'),
        ('ARCHIVED', '已归档'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_number = models.CharField(max_length=100, unique=True, verbose_name='报告编号')
    plan = models.ForeignKey(
        InspectionPlan, on_delete=models.CASCADE,
        related_name='reports', verbose_name='检验计划'
    )
    batch = models.ForeignKey(
        MeasurementBatch, on_delete=models.CASCADE,
        related_name='reports', verbose_name='测量批次'
    )
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.SET_NULL,
        null=True, verbose_name='报告模板'
    )
    
    # 报告信息
    title = models.CharField(max_length=200, verbose_name='报告标题')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name='状态'
    )
    
    # 文件
    pdf_file = models.FileField(
        upload_to=report_upload_path,
        blank=True, null=True, verbose_name='PDF文件'
    )
    
    # 时间信息
    generated_at = models.DateTimeField(null=True, blank=True, verbose_name='生成时间')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    
    # 人员
    generated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='generated_reports',
        verbose_name='生成人'
    )
    published_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='published_reports',
        verbose_name='发布人'
    )
    
    # 总结
    summary = models.TextField(blank=True, verbose_name='报告总结')
    conclusion = models.CharField(max_length=20, blank=True, verbose_name='结论')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'inspection_reports'
        verbose_name = '检验报告'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_number} - {self.title}"

    @property
    def material_compliant(self):
        """Form2材料证书是否全部合规（无记录时视为未填写，返回None）"""
        certs = self.material_certifications.all()
        if not certs.exists():
            return None
        return all(c.compliant for c in certs)

    @property
    def special_process_compliant(self):
        """Form2特殊工艺是否全部合规（无记录时视为未填写，返回None）"""
        records = self.special_processes.all()
        if not records.exists():
            return None
        return all(r.compliant for r in records)

    @property
    def functional_test_compliant(self):
        """Form2功能测试是否全部合规（无记录时视为未填写，返回None）"""
        records = self.functional_tests.all()
        if not records.exists():
            return None
        return all(r.compliant for r in records)


def form2_attachment_upload_path(instance, filename):
    """AS9102 Form2附件（材料证书/工艺证书/测试报告）上传路径"""
    return f'reports/{instance.report.report_number}/form2/{filename}'


class MaterialCertification(models.Model):
    """AS9102 Form2 - 原材料证书"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        InspectionReport, on_delete=models.CASCADE,
        related_name='material_certifications', verbose_name='检验报告'
    )
    material_spec = models.CharField(max_length=200, verbose_name='材料规范/牌号')
    cert_number = models.CharField(max_length=100, blank=True, verbose_name='证书编号')
    supplier = models.CharField(max_length=200, blank=True, verbose_name='供应商')
    batch_number = models.CharField(max_length=100, blank=True, verbose_name='批次/炉批号')
    compliant = models.BooleanField(default=True, verbose_name='符合要求')
    attachment = models.FileField(
        upload_to=form2_attachment_upload_path,
        blank=True, null=True, verbose_name='证书附件'
    )
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'material_certifications'
        verbose_name = 'Form2-原材料证书'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.material_spec} - {self.cert_number or '未编号'}"


class SpecialProcessRecord(models.Model):
    """AS9102 Form2 - 特殊工艺记录（热处理/无损检测/电镀/焊接/涂层等）"""
    PROCESS_TYPE_CHOICES = [
        ('HEAT_TREATMENT', '热处理'),
        ('NDT', '无损检测'),
        ('PLATING', '电镀'),
        ('WELDING', '焊接'),
        ('COATING', '涂层/喷涂'),
        ('PAINTING', '涂装'),
        ('OTHER', '其他'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        InspectionReport, on_delete=models.CASCADE,
        related_name='special_processes', verbose_name='检验报告'
    )
    process_type = models.CharField(
        max_length=20, choices=PROCESS_TYPE_CHOICES,
        verbose_name='工艺类型'
    )
    spec_number = models.CharField(max_length=100, blank=True, verbose_name='执行规范编号')
    processor = models.CharField(max_length=200, blank=True, verbose_name='工艺供方/承做单位')
    cert_number = models.CharField(max_length=100, blank=True, verbose_name='合格证编号')
    compliant = models.BooleanField(default=True, verbose_name='符合要求')
    attachment = models.FileField(
        upload_to=form2_attachment_upload_path,
        blank=True, null=True, verbose_name='合格证附件'
    )
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'special_process_records'
        verbose_name = 'Form2-特殊工艺记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_process_type_display()} - {self.cert_number or '未编号'}"


class FunctionalTestRecord(models.Model):
    """AS9102 Form2 - 功能测试记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        InspectionReport, on_delete=models.CASCADE,
        related_name='functional_tests', verbose_name='检验报告'
    )
    test_name = models.CharField(max_length=200, verbose_name='测试项目')
    spec_reference = models.CharField(max_length=200, blank=True, verbose_name='依据规范/图纸要求')
    result_summary = models.TextField(blank=True, verbose_name='测试结果摘要')
    compliant = models.BooleanField(default=True, verbose_name='符合要求')
    attachment = models.FileField(
        upload_to=form2_attachment_upload_path,
        blank=True, null=True, verbose_name='测试报告附件'
    )
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'functional_test_records'
        verbose_name = 'Form2-功能测试记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.test_name
