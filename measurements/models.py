from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from inspections.models import InspectionPlan, InspectionCharacteristic
import uuid


class MeasurementBatch(models.Model):
    """测量批次"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('IN_PROGRESS', '测量中'),
        ('COMPLETED', '已完成'),
        ('REVIEWED', '已审核'),
        ('APPROVED', '已批准'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_number = models.CharField(max_length=100, unique=True, verbose_name='批次号')
    plan = models.ForeignKey(
        InspectionPlan, on_delete=models.CASCADE,
        related_name='batches', verbose_name='检验计划'
    )
    
    # 样本信息
    sample_size = models.PositiveIntegerField(default=1, verbose_name='样本数量')
    
    # 设备信息
    equipment_type = models.CharField(max_length=50, blank=True, default='', verbose_name='设备类型')
    equipment_id = models.CharField(max_length=100, blank=True, default='', verbose_name='设备编号')
    equipment_name = models.CharField(max_length=200, blank=True, default='', verbose_name='设备名称')
    
    # 环境条件
    environment_temp = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True, verbose_name='温度(℃)'
    )
    environment_humidity = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True, verbose_name='湿度(%)'
    )
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name='状态'
    )
    
    # 测量人员
    measured_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='测量人员'
    )
    measured_at = models.DateTimeField(null=True, blank=True, verbose_name='测量时间')
    
    # 审核信息
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_batches',
        verbose_name='审核人员'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'measurement_batches'
        verbose_name = '测量批次'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.batch_number} - {self.plan.plan_number if self.plan else 'N/A'}"
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            count = MeasurementBatch.objects.filter(
                batch_number__startswith=f'MB-{date_str}'
            ).count()
            self.batch_number = f'MB-{date_str}-{count+1:04d}'
        if not self.measured_at:
            from django.utils import timezone
            self.measured_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def total_measurements(self):
        """总测量数"""
        return self.records.count()
    
    @property
    def pass_count(self):
        """通过数量"""
        return self.records.filter(status='PASS').count()
    
    @property
    def fail_count(self):
        """失败数量"""
        return self.records.filter(status='FAIL').count()

    @property
    def pass_rate(self):
        """合格率(%)"""
        total = self.total_measurements
        if total == 0:
            return 0
        return round(self.pass_count / total * 100)
    
    def calculate_all_statistics(self):
        """计算批次所有特性的统计数据"""
        import math
        from decimal import Decimal
        
        characteristics = self.plan.characteristics.all()
        calculated_count = 0
        
        for char in characteristics:
            records = MeasurementRecord.objects.filter(
                batch=self, characteristic=char
            )
            
            if not records.exists():
                continue
            
            # 计算统计指标
            values = [r.measured_value for r in records]
            n = len(values)
            mean = sum(values) / n

            # 样本标准差（n-1分母，符合AIAG SPC手册与AS9102惯例；样本数<2时无法估计离散度）
            if n >= 2:
                variance = sum((v - mean) ** 2 for v in values) / (n - 1)
                std_dev = Decimal(str(math.sqrt(variance)))
            else:
                std_dev = Decimal('0')

            # 极值
            min_value = min(values)
            max_value = max(values)
            range_value = max_value - min_value

            # 过程能力指数（支持单侧公差：只有上限/只有下限的特性，如平面度、位置度等GD&T）
            upper_limit = char.upper_limit
            lower_limit = char.lower_limit

            if std_dev > 0:
                cpu = (upper_limit - mean) / (3 * std_dev) if upper_limit is not None else None
                cpl = (mean - lower_limit) / (3 * std_dev) if lower_limit is not None else None

                if cpu is not None and cpl is not None:
                    cpk = min(cpu, cpl)
                    # Cp仅在双侧公差下有经典定义
                    tolerance_band = upper_limit - lower_limit
                    cp = tolerance_band / (6 * std_dev)
                elif cpu is not None:
                    cpk = cpu
                    cp = None
                elif cpl is not None:
                    cpk = cpl
                    cp = None
                else:
                    cpk = None
                    cp = None
            else:
                cp = None
                cpk = None

            # 保存统计结果（过程能力评价由StatisticalAnalysis.process_capability属性按cpk实时计算）
            StatisticalAnalysis.objects.update_or_create(
                characteristic=char,
                batch=self,
                defaults={
                    'sample_count': len(values),
                    'mean': mean,
                    'std_dev': std_dev,
                    'min_value': min_value,
                    'max_value': max_value,
                    'range_value': range_value,
                    'cp': cp,
                    'cpk': cpk
                }
            )
            calculated_count += 1
        
        return calculated_count


class MeasurementRecord(models.Model):
    """测量记录"""
    STATUS_CHOICES = [
        ('PASS', '通过'),
        ('FAIL', '失败'),
        ('PENDING', '待定'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        MeasurementBatch, on_delete=models.CASCADE,
        related_name='records', verbose_name='测量批次'
    )
    characteristic = models.ForeignKey(
        InspectionCharacteristic, on_delete=models.CASCADE,
        related_name='measurements', verbose_name='检验特性'
    )
    
    # 样本序号
    sample_number = models.PositiveIntegerField(default=1, verbose_name='样本序号')
    
    # 测量值
    measured_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='实测值'
    )
    
    # 偏差
    deviation = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='偏差'
    )
    
    # 判定结果
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        verbose_name='状态'
    )
    
    # 测量时间
    measured_at = models.DateTimeField(auto_now_add=True, verbose_name='测量时间')
    
    # 备注
    notes = models.TextField(blank=True, verbose_name='备注')
    
    class Meta:
        db_table = 'measurement_records'
        verbose_name = '测量记录'
        verbose_name_plural = verbose_name
        ordering = ['characteristic__sequence', 'sample_number']
        unique_together = ['batch', 'characteristic', 'sample_number']
    
    def __str__(self):
        return f"{self.characteristic.char_number} - 样本{self.sample_number}"
    
    def save(self, *args, **kwargs):
        # 自动计算偏差
        self.deviation = self.measured_value - self.characteristic.nominal_value
        
        # 自动判定（单侧公差时，无上限/下限的一侧不参与判定）
        upper_limit = self.characteristic.upper_limit
        lower_limit = self.characteristic.lower_limit

        if upper_limit is not None and self.measured_value > upper_limit:
            self.status = 'FAIL'
        elif lower_limit is not None and self.measured_value < lower_limit:
            self.status = 'FAIL'
        else:
            self.status = 'PASS'
        
        super().save(*args, **kwargs)


class StatisticalAnalysis(models.Model):
    """统计分析"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    characteristic = models.ForeignKey(
        InspectionCharacteristic, on_delete=models.CASCADE,
        related_name='statistics', verbose_name='检验特性'
    )
    batch = models.ForeignKey(
        MeasurementBatch, on_delete=models.CASCADE,
        related_name='statistics', verbose_name='测量批次'
    )
    
    # 统计指标
    sample_count = models.PositiveIntegerField(verbose_name='样本数')
    mean = models.DecimalField(max_digits=15, decimal_places=6, verbose_name='平均值')
    std_dev = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='标准差'
    )
    min_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='最小值'
    )
    max_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='最大值'
    )
    range_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='极差'
    )
    
    # 过程能力指数
    cp = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True, verbose_name='Cp'
    )
    cpk = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True, verbose_name='Cpk'
    )
    
    calculated_at = models.DateTimeField(auto_now_add=True, verbose_name='计算时间')
    
    class Meta:
        db_table = 'statistical_analyses'
        verbose_name = '统计分析'
        verbose_name_plural = verbose_name
        unique_together = ['characteristic', 'batch']
    
    # 行业惯例：Cpk作为长期过程能力指标通常需要≥30个样本才具有统计意义；
    # FAI首件检验阶段样本量通常仅3~5件，计算出的Cpk仅供参考，不能视为正式过程能力结论
    MIN_RELIABLE_SAMPLE_SIZE = 30

    def __str__(self):
        return f"{self.characteristic.char_number} - Cpk: {self.cpk}"

    @property
    def is_small_sample(self):
        """样本量是否小于可靠估计过程能力所需的最小样本数（提醒：FAI阶段Cpk仅供参考）"""
        return self.sample_count < self.MIN_RELIABLE_SAMPLE_SIZE

    @property
    def process_capability(self):
        """过程能力评价"""
        if self.cpk is None:
            return 'N/A'
        if self.cpk >= 1.67:
            return '优秀'
        elif self.cpk >= 1.33:
            return '良好'
        elif self.cpk >= 1.0:
            return '合格'
        else:
            return '不足'
