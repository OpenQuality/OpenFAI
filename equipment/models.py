from django.db import models
from django.contrib.auth.models import User
import uuid


class Equipment(models.Model):
    """测量设备"""
    EQUIPMENT_TYPE_CHOICES = [
        ('CMM', '三坐标测量机'),
        ('OPTICAL', '光学测量仪'),
        ('LASER', '激光扫描仪'),
        ('VISION', '影像测量仪'),
        ('MECHANICAL', '机械测量设备'),
        ('OTHER', '其他'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', '正常'),
        ('MAINTENANCE', '维护中'),
        ('CALIBRATION', '校准中'),
        ('INACTIVE', '停用'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment_id = models.CharField(max_length=100, unique=True, verbose_name='设备编号')
    equipment_name = models.CharField(max_length=200, verbose_name='设备名称')
    equipment_type = models.CharField(
        max_length=20, choices=EQUIPMENT_TYPE_CHOICES,
        verbose_name='设备类型'
    )
    
    # 设备信息
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name='制造商')
    model = models.CharField(max_length=100, blank=True, verbose_name='型号')
    serial_number = models.CharField(max_length=100, blank=True, verbose_name='序列号')
    
    # 连接信息
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    port = models.PositiveIntegerField(null=True, blank=True, verbose_name='端口')
    connection_string = models.CharField(max_length=500, blank=True, verbose_name='连接字符串')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='ACTIVE', verbose_name='状态'
    )
    
    # 校准信息
    last_calibration_date = models.DateField(null=True, blank=True, verbose_name='上次校准日期')
    next_calibration_date = models.DateField(null=True, blank=True, verbose_name='下次校准日期')
    calibration_certificate = models.CharField(max_length=100, blank=True, verbose_name='校准证书')
    
    # 负责人
    responsible_person = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='负责人'
    )
    
    # 备注
    location = models.CharField(max_length=200, blank=True, verbose_name='存放位置')
    notes = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'equipment'
        verbose_name = '测量设备'
        verbose_name_plural = verbose_name
        ordering = ['equipment_id']
    
    def __str__(self):
        return f"{self.equipment_id} - {self.equipment_name}"


class EquipmentConnection(models.Model):
    """设备连接记录"""
    STATUS_CHOICES = [
        ('CONNECTED', '已连接'),
        ('DISCONNECTED', '已断开'),
        ('ERROR', '错误'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE,
        related_name='connections', verbose_name='设备'
    )
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        verbose_name='状态'
    )
    
    connected_at = models.DateTimeField(auto_now_add=True, verbose_name='连接时间')
    disconnected_at = models.DateTimeField(null=True, blank=True, verbose_name='断开时间')
    
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    
    class Meta:
        db_table = 'equipment_connections'
        verbose_name = '设备连接'
        verbose_name_plural = verbose_name
        ordering = ['-connected_at']


class MeasurementDataImport(models.Model):
    """测量数据导入记录"""
    STATUS_CHOICES = [
        ('PENDING', '待处理'),
        ('PROCESSING', '处理中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE,
        related_name='imports', verbose_name='设备'
    )
    
    # 导入文件
    file_name = models.CharField(max_length=255, verbose_name='文件名')
    file_data = models.BinaryField(null=True, blank=True, verbose_name='文件数据')
    
    # 解析数据
    parsed_data = models.JSONField(default=dict, blank=True, verbose_name='解析数据')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    
    # 统计
    total_records = models.PositiveIntegerField(default=0, verbose_name='总记录数')
    imported_records = models.PositiveIntegerField(default=0, verbose_name='已导入记录数')
    error_records = models.PositiveIntegerField(default=0, verbose_name='错误记录数')
    
    # 错误信息
    error_log = models.TextField(blank=True, verbose_name='错误日志')
    
    imported_at = models.DateTimeField(null=True, blank=True, verbose_name='导入时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name='创建人'
    )
    
    class Meta:
        db_table = 'measurement_imports'
        verbose_name = '测量数据导入'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.equipment.equipment_id} - {self.file_name}"
