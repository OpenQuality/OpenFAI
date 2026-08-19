from django.db import models
from django.contrib.auth.models import User
from core.models import BaseModel
import os


def cad_file_upload_path(instance, filename):
    """CAD文件上传路径"""
    return f'cad_files/{instance.part_number}/{filename}'


def drawing_upload_path(instance, filename):
    """图片文件上传路径 - 保持原始文件名"""
    return f'drawings/{filename}'


def document_upload_path(instance, filename):
    """文档文件上传路径 - 保持原始文件名"""
    return f'documents/{filename}'


def model_3d_upload_path(instance, filename):
    """3D模型文件上传路径 - 保持原始文件名"""
    return f'models_3d/{filename}'


class Part(BaseModel):
    """零件"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('ACTIVE', '激活'),
        ('OBSOLETE', '作废'),
        ('PENDING', '待审核'),
    ]
    
    part_number = models.CharField(max_length=100, unique=True, verbose_name='零件编号')
    part_name = models.CharField(max_length=200, verbose_name='零件名称')
    revision = models.CharField(max_length=20, default='A', verbose_name='版本号')
    description = models.TextField(blank=True, verbose_name='描述')
    
    # 文件 - 支持多种格式
    cad_file = models.FileField(
        upload_to=cad_file_upload_path, 
        blank=True, null=True, verbose_name='CAD文件',
        help_text='仅存储，不支持解析。格式: DWG, DXF, SLDPRT, CATPART, PRT, STEP'
    )
    cad_file_type = models.CharField(max_length=20, blank=True, null=True, default='', verbose_name='CAD文件类型')
    
    drawing_file = models.FileField(
        upload_to=drawing_upload_path,
        blank=True, null=True, verbose_name='图片文件',
        help_text='支持OCR识别。格式: PNG, JPG, BMP, GIF'
    )
    
    # 新增：PDF文件字段
    pdf_file = models.FileField(
        upload_to=document_upload_path,
        blank=True, null=True, verbose_name='PDF文档',
        help_text='支持OCR识别。格式: PDF'
    )
    
    # 新增：3D模型文件支持
    model_3d_file = models.FileField(
        upload_to=model_3d_upload_path,
        blank=True, null=True, verbose_name='3D模型文件',
        help_text='支持解析。格式: STEP(.stp/.step), IGES(.igs/.iges), STL, OBJ, PLY'
    )
    model_3d_file_type = models.CharField(max_length=20, blank=True, null=True, default='', verbose_name='3D文件类型')
    
    # 文件元信息（JSON字段，避免数据库列约束问题）
    # 存储格式: {"cad": {"original_name": "xxx.pdf", "size": 1234}, ...}
    file_metadata = models.JSONField(default=dict, blank=True, verbose_name='文件元信息')
    
    # 基础信息
    material = models.CharField(max_length=100, blank=True, verbose_name='材料')
    weight = models.DecimalField(
        max_digits=10, decimal_places=3, 
        null=True, blank=True, verbose_name='重量(kg)'
    )
    surface_treatment = models.CharField(max_length=200, blank=True, verbose_name='表面处理')
    
    # 客户信息
    customer = models.CharField(max_length=200, blank=True, verbose_name='客户')
    customer_part_number = models.CharField(max_length=100, blank=True, verbose_name='客户零件编号')
    
    # 产品信息（新增字段）
    batch_serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='批次/序列号')
    order_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='订单号')
    production_quantity = models.PositiveIntegerField(default=0, verbose_name='生产数量')
    fai_quantity = models.PositiveIntegerField(default=1, verbose_name='首件数量')
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='单位/部门')
    operator = models.CharField(max_length=100, blank=True, null=True, verbose_name='操作者')
    
    # 状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, 
        default='DRAFT', verbose_name='状态'
    )
    
    class Meta:
        db_table = 'parts'
        verbose_name = '零件'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.part_number} - {self.part_name} (Rev.{self.revision})"
    
    @property
    def cad_filename(self):
        # 优先使用保存的原始文件名
        if self.file_metadata:
            meta = self.file_metadata.get('cad', {})
            if meta.get('original_name'):
                return meta['original_name']
        if self.cad_file:
            return os.path.basename(self.cad_file.name)
        return ''
    
    @property
    def drawing_filename(self):
        # 优先使用保存的原始文件名
        if self.file_metadata:
            meta = self.file_metadata.get('drawing', {})
            if meta.get('original_name'):
                return meta['original_name']
        if self.drawing_file:
            return os.path.basename(self.drawing_file.name)
        return ''
    
    @property
    def pdf_filename(self):
        # 优先使用保存的原始文件名
        if self.file_metadata:
            meta = self.file_metadata.get('pdf', {})
            if meta.get('original_name'):
                return meta['original_name']
        if self.pdf_file:
            return os.path.basename(self.pdf_file.name)
        return ''
    
    @property
    def model_3d_filename(self):
        # 优先使用保存的原始文件名
        if self.file_metadata:
            meta = self.file_metadata.get('model_3d', {})
            if meta.get('original_name'):
                return meta['original_name']
        if self.model_3d_file:
            return os.path.basename(self.model_3d_file.name)
        return ''
    
    def get_all_files(self):
        """获取所有上传的文件，包含OCR识别状态"""
        from parts.models import CADExtraction
        
        # 获取该零件所有的识别记录，建立文件名->状态的映射
        extractions = CADExtraction.objects.filter(part=self).order_by('-created_at')
        file_status_map = {}
        # 同时记录文件类型标签的状态（兼容旧数据）
        type_status_map = {}
        
        for ext in extractions:
            # 兼容处理：extraction_data可能是列表或字典
            if isinstance(ext.extraction_data, dict):
                source_file = ext.extraction_data.get('source_file', '')
                source_type = ext.extraction_data.get('source_type', '')
            else:
                source_file = ''
                source_type = ''
            
            if source_file:
                # 记录文件名->状态
                if source_file not in file_status_map:
                    file_status_map[source_file] = ext.status
                # 兼容旧数据：source_file可能是"PDF文档"、"图片文件"等标签
                if source_file == 'PDF文档':
                    type_status_map['pdf'] = ext.status
                elif source_file == '图片文件':
                    type_status_map['drawing'] = ext.status
                elif source_file == 'CAD文件':
                    type_status_map['cad'] = ext.status
        
        # 获取文件元信息
        metadata = self.file_metadata or {}
        
        files = []
        if self.cad_file:
            # 优先使用保存的原始文件名
            meta = metadata.get('cad', {})
            file_name = meta.get('original_name') or self.cad_filename
            # 优先使用保存的文件大小
            size = meta.get('size') or (self.cad_file.size if self.cad_file else 0)
            status = file_status_map.get(file_name) or type_status_map.get('cad', 'PENDING')
            files.append({
                'type': 'cad',
                'name': file_name,
                'url': self.cad_file.url,
                'extension': os.path.splitext(file_name)[1].upper() if file_name else '',
                'ocr_status': status,
                'size': size
            })
        if self.drawing_file:
            meta = metadata.get('drawing', {})
            file_name = meta.get('original_name') or self.drawing_filename
            size = meta.get('size') or (self.drawing_file.size if self.drawing_file else 0)
            status = file_status_map.get(file_name) or type_status_map.get('drawing', 'PENDING')
            files.append({
                'type': 'drawing',
                'name': file_name,
                'url': self.drawing_file.url,
                'extension': os.path.splitext(file_name)[1].upper() if file_name else '',
                'ocr_status': status,
                'size': size
            })
        if self.pdf_file:
            meta = metadata.get('pdf', {})
            file_name = meta.get('original_name') or self.pdf_filename
            size = meta.get('size') or (self.pdf_file.size if self.pdf_file else 0)
            status = file_status_map.get(file_name) or type_status_map.get('pdf', 'PENDING')
            files.append({
                'type': 'pdf',
                'name': file_name,
                'url': self.pdf_file.url,
                'extension': '.PDF',
                'ocr_status': status,
                'size': size
            })
        if self.model_3d_file:
            meta = metadata.get('model_3d', {})
            file_name = meta.get('original_name') or self.model_3d_filename
            size = meta.get('size') or (self.model_3d_file.size if self.model_3d_file else 0)
            files.append({
                'type': '3d_model',
                'name': file_name,
                'url': self.model_3d_file.url,
                'extension': os.path.splitext(file_name)[1].upper() if file_name else '',
                'ocr_status': 'N/A',  # 3D模型不支持OCR
                'size': size
            })
        return files


class PartAttachment(models.Model):
    """零件附件 - 支持多文件上传"""
    FILE_TYPE_CHOICES = [
        ('PDF', 'PDF文档'),
        ('IMAGE', '图片文件'),
        ('CAD', 'CAD文件'),
        ('MODEL_3D', '3D模型'),
        ('OTHER', '其他'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '待识别'),
        ('PROCESSING', '识别中'),
        ('COMPLETED', '识别完成'),
        ('FAILED', '识别失败'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='attachments', verbose_name='零件'
    )
    
    # 文件信息
    file = models.FileField(upload_to='part_attachments/%Y%m/%d/', verbose_name='附件文件')
    file_name = models.CharField(max_length=255, verbose_name='原始文件名')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, verbose_name='文件类型')
    file_size = models.PositiveIntegerField(default=0, verbose_name='文件大小(字节)')
    
    # 识别状态
    ocr_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='OCR状态')
    ocr_data = models.JSONField(default=dict, blank=True, verbose_name='OCR识别数据')
    ocr_error = models.TextField(blank=True, verbose_name='OCR错误信息')
    
    # 提取的特征（用于CAD/3D模型）
    extracted_features = models.JSONField(default=dict, blank=True, verbose_name='提取的特征')
    
    # 元信息
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='part_attachments', verbose_name='上传人'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    description = models.CharField(max_length=500, blank=True, verbose_name='描述')
    
    class Meta:
        db_table = 'part_attachments'
        verbose_name = '零件附件'
        verbose_name_plural = verbose_name
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.get_file_type_display()})"
    
    def save(self, *args, **kwargs):
        if not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        if not self.file_size and self.file:
            self.file_size = self.file.size
        if not self.file_type:
            self._detect_file_type()
        super().save(*args, **kwargs)
    
    def _detect_file_type(self):
        """自动检测文件类型"""
        ext = os.path.splitext(self.file_name)[1].lower()
        if ext in ['.pdf']:
            self.file_type = 'PDF'
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
            self.file_type = 'IMAGE'
        elif ext in ['.dwg', '.dxf', '.sldprt', '.catpart', '.prt', '.stp', '.step', '.iges', '.igs', '.stl', '.obj', '.ply']:
            self.file_type = 'CAD'
            if ext in ['.stp', '.step', '.iges', '.igs', '.stl', '.obj', '.ply']:
                self.file_type = 'MODEL_3D'
        else:
            self.file_type = 'OTHER'


class CADExtraction(models.Model):
    """CAD解析记录"""
    STATUS_CHOICES = [
        ('PENDING', '待解析'),
        ('PROCESSING', '解析中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='extractions', verbose_name='零件'
    )
    extraction_data = models.JSONField(default=dict, blank=True, verbose_name='提取数据')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    extracted_at = models.DateTimeField(null=True, blank=True, verbose_name='提取时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    # 人工复核闸口：AI/OCR识别结果默认未经核实，必须由人工确认（或修正后确认）
    # 才能用于生成正式检验特性，避免错误的识别结果未经核查直接进入正式FAI流程
    reviewed = models.BooleanField(default=False, verbose_name='已人工复核')
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_extractions',
        verbose_name='复核人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='复核时间')

    class Meta:
        db_table = 'cad_extractions'
        verbose_name = 'CAD解析记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.part.part_number} - {self.status}"


class Dimension(models.Model):
    """提取的尺寸信息"""
    DIMENSION_TYPE_CHOICES = [
        ('LINEAR', '线性尺寸'),
        ('ANGULAR', '角度尺寸'),
        ('DIAMETER', '直径'),
        ('RADIUS', '半径'),
        ('GD_T', '形位公差'),
        ('SURFACE', '表面粗糙度'),
    ]
    
    extraction = models.ForeignKey(
        CADExtraction, on_delete=models.CASCADE,
        related_name='dimensions', verbose_name='解析记录'
    )
    dim_id = models.CharField(max_length=50, verbose_name='尺寸ID')
    dim_type = models.CharField(
        max_length=20, choices=DIMENSION_TYPE_CHOICES,
        verbose_name='尺寸类型'
    )
    name = models.CharField(max_length=200, verbose_name='尺寸名称')
    nominal_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name='理论值'
    )
    upper_tolerance = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True, verbose_name='上公差',
        help_text='为空表示未识别到明确标注或为单侧公差，需人工核实'
    )
    lower_tolerance = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True, verbose_name='下公差',
        help_text='为空表示未识别到明确标注或为单侧公差，需人工核实'
    )
    unit = models.CharField(max_length=10, default='mm', verbose_name='单位')
    is_critical = models.BooleanField(default=False, verbose_name='是否关键特性')
    tolerance_verified = models.BooleanField(
        default=False, verbose_name='公差已人工核实',
        help_text='AI/OCR识别结果默认未核实，需人工确认或修正后才能生成正式检验特性'
    )
    position = models.JSONField(
        null=True, blank=True, verbose_name='图纸标注位置',
        help_text='格式{"x": 0-100, "y": 0-100}，表示该尺寸标注在图纸图片中的百分比坐标，用于气泡图定位；为空表示识别引擎未返回位置信息'
    )
    notes = models.TextField(blank=True, verbose_name='备注')
    
    class Meta:
        db_table = 'dimensions'
        verbose_name = '尺寸'
        verbose_name_plural = verbose_name
        ordering = ['dim_id']
    
    def __str__(self):
        return f"{self.dim_id} - {self.name}"
    
    @property
    def tolerance_range(self):
        """公差范围"""
        lower = self.lower_tolerance if self.lower_tolerance is not None else '无下限'
        upper = self.upper_tolerance if self.upper_tolerance is not None else '无上限'
        return f"{lower} / {upper}"


class DimensionTemplate(models.Model):
    """尺寸模板 - 用于保存和复用识别配置"""
    TEMPLATE_TYPE_CHOICES = [
        ('SHAFT', '轴类零件'),
        ('PLATE', '板类零件'),
        ('HOUSING', '壳体零件'),
        ('CUSTOM', '自定义'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='模板描述')
    template_type = models.CharField(
        max_length=20, choices=TEMPLATE_TYPE_CHOICES,
        default='CUSTOM', verbose_name='模板类型'
    )
    dimensions_data = models.JSONField(default=list, verbose_name='尺寸数据')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='创建者'
    )
    is_public = models.BooleanField(default=True, verbose_name='公开')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'dimension_templates'
        verbose_name = '尺寸模板'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_dimensions_count(self):
        """获取尺寸数量"""
        return len(self.dimensions_data) if self.dimensions_data else 0


class ControlRequirement(models.Model):
    """控制要求 - 从图纸解析出的关键控制点"""
    RISK_LEVEL_CHOICES = [
        ('HIGH', '高风险'),
        ('MEDIUM', '中风险'),
        ('LOW', '低风险'),
    ]
    
    CONTROL_TYPE_CHOICES = [
        ('DIMENSION', '尺寸控制'),
        ('SURFACE', '表面质量'),
        ('MATERIAL', '材料要求'),
        ('GEOMETRY', '形位公差'),
        ('PROCESS', '工艺要求'),
        ('ASSEMBLY', '装配要求'),
        ('SAFETY', '安全要求'),
        ('OTHER', '其他'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='control_requirements', verbose_name='零件'
    )
    extraction = models.ForeignKey(
        CADExtraction, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='control_requirements',
        verbose_name='关联解析记录'
    )
    
    # 控制要求基本信息
    requirement_id = models.CharField(max_length=50, verbose_name='要求编号')
    requirement_name = models.CharField(max_length=200, verbose_name='要求名称')
    control_type = models.CharField(
        max_length=20, choices=CONTROL_TYPE_CHOICES,
        verbose_name='控制类型'
    )
    description = models.TextField(verbose_name='要求描述')
    
    # 规格和公差
    nominal_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='标称值'
    )
    upper_limit = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='上限'
    )
    lower_limit = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='下限'
    )
    unit = models.CharField(max_length=10, blank=True, verbose_name='单位')
    
    # 风险评估
    risk_level = models.CharField(
        max_length=10, choices=RISK_LEVEL_CHOICES,
        default='MEDIUM', verbose_name='风险等级'
    )
    risk_factors = models.JSONField(default=list, blank=True, verbose_name='风险因素')
    impact_analysis = models.TextField(blank=True, verbose_name='影响分析')
    
    # 检测方法
    inspection_method = models.CharField(max_length=200, blank=True, verbose_name='检测方法')
    inspection_tool = models.CharField(max_length=200, blank=True, verbose_name='检测工具')
    inspection_frequency = models.CharField(max_length=100, blank=True, verbose_name='检测频次')
    
    # 关联的尺寸
    related_dimension = models.ForeignKey(
        Dimension, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='关联尺寸'
    )
    
    # 是否关键特性
    is_key_characteristic = models.BooleanField(default=False, verbose_name='是否关键特性')
    is_safety_critical = models.BooleanField(default=False, verbose_name='是否安全关键')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'control_requirements'
        verbose_name = '控制要求'
        verbose_name_plural = verbose_name
        ordering = ['requirement_id']
    
    def __str__(self):
        return f"{self.requirement_id} - {self.requirement_name}"


class RiskPoint(models.Model):
    """关键风险点"""
    SEVERITY_CHOICES = [
        ('CRITICAL', '严重'),
        ('MAJOR', '重要'),
        ('MINOR', '次要'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='risk_points', verbose_name='零件'
    )
    
    # 风险点信息
    risk_id = models.CharField(max_length=50, verbose_name='风险编号')
    risk_name = models.CharField(max_length=200, verbose_name='风险名称')
    description = models.TextField(verbose_name='风险描述')
    
    # 风险分类
    risk_category = models.CharField(max_length=100, blank=True, verbose_name='风险类别')
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES,
        default='MAJOR', verbose_name='严重程度'
    )
    probability = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=0.5, verbose_name='发生概率'
    )
    
    # 影响范围
    affected_dimensions = models.JSONField(default=list, blank=True, verbose_name='影响尺寸')
    affected_processes = models.JSONField(default=list, blank=True, verbose_name='影响工序')
    
    # 预防和纠正措施
    prevention_measures = models.TextField(blank=True, verbose_name='预防措施')
    correction_measures = models.TextField(blank=True, verbose_name='纠正措施')
    contingency_plan = models.TextField(blank=True, verbose_name='应急预案')
    
    # 关联控制要求
    related_requirements = models.ManyToManyField(
        ControlRequirement, blank=True,
        related_name='risk_points', verbose_name='关联控制要求'
    )
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'risk_points'
        verbose_name = '关键风险点'
        verbose_name_plural = verbose_name
        ordering = ['-severity', 'risk_id']
    
    def __str__(self):
        return f"{self.risk_id} - {self.risk_name}"


class SOPDocument(models.Model):
    """SOP标准操作程序文档"""
    DOCUMENT_TYPE_CHOICES = [
        ('SOP', '标准操作程序'),
        ('WORK_INSTRUCTION', '作业指导书'),
        ('INSPECTION_GUIDE', '检验指导书'),
        ('CONTROL_PLAN', '控制计划'),
        ('INTERNAL_GUIDE', '内部建议指导书'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('REVIEW', '审核中'),
        ('APPROVED', '已批准'),
        ('PUBLISHED', '已发布'),
        ('OBSOLETE', '已作废'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='sop_documents', verbose_name='零件'
    )
    extraction = models.ForeignKey(
        CADExtraction, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sop_documents',
        verbose_name='关联解析记录'
    )
    
    # 文档基本信息
    document_number = models.CharField(max_length=100, unique=True, verbose_name='文档编号')
    document_title = models.CharField(max_length=200, verbose_name='文档标题')
    document_type = models.CharField(
        max_length=30, choices=DOCUMENT_TYPE_CHOICES,
        default='SOP', verbose_name='文档类型'
    )
    version = models.CharField(max_length=20, default='1.0', verbose_name='版本号')
    
    # 文档内容
    content = models.TextField(verbose_name='文档内容')
    sections = models.JSONField(default=list, blank=True, verbose_name='章节结构')
    
    # 关联的控制要求和风险点
    control_requirements = models.ManyToManyField(
        ControlRequirement, blank=True,
        related_name='sop_documents', verbose_name='控制要求'
    )
    risk_points = models.ManyToManyField(
        RiskPoint, blank=True,
        related_name='sop_documents', verbose_name='风险点'
    )
    
    # 状态和审批
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='DRAFT', verbose_name='状态'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, related_name='created_sop_documents',
        verbose_name='创建人'
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_sop_documents',
        verbose_name='审核人'
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_sop_documents',
        verbose_name='批准人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='批准时间')
    
    # 生效日期
    effective_date = models.DateField(null=True, blank=True, verbose_name='生效日期')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='失效日期')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'sop_documents'
        verbose_name = 'SOP文档'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document_number} - {self.document_title}"


class Model3DAnalysis(models.Model):
    """3D模型解析结果"""
    STATUS_CHOICES = [
        ('PENDING', '待解析'),
        ('PROCESSING', '解析中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='model_3d_analyses', verbose_name='零件'
    )
    
    # 解析状态
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='PENDING', verbose_name='状态'
    )
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    
    # 模型信息
    file_format = models.CharField(max_length=20, verbose_name='文件格式')
    file_size = models.PositiveIntegerField(default=0, verbose_name='文件大小(字节)')
    
    # 几何信息
    vertex_count = models.PositiveIntegerField(default=0, verbose_name='顶点数量')
    face_count = models.PositiveIntegerField(default=0, verbose_name='面数量')
    edge_count = models.PositiveIntegerField(default=0, verbose_name='边数量')
    
    # 边界框
    bounding_box = models.JSONField(default=dict, blank=True, verbose_name='边界框')
    # 格式: {'min': [x, y, z], 'max': [x, y, z]}
    
    # 体积和面积
    volume = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='体积(mm³)'
    )
    surface_area = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='表面积(mm²)'
    )
    
    # 解析数据
    geometry_data = models.JSONField(default=dict, blank=True, verbose_name='几何数据')
    mesh_data = models.JSONField(default=dict, blank=True, verbose_name='网格数据')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='元数据')
    
    # 提取的特征
    features = models.JSONField(default=list, blank=True, verbose_name='提取特征')
    # 示例: [{'type': 'hole', 'diameter': 10, 'depth': 20, 'position': [x,y,z]}, ...]
    
    # 关联的尺寸和控制要求
    extracted_dimensions = models.ManyToManyField(
        Dimension, blank=True,
        related_name='model_3d_analyses', verbose_name='提取尺寸'
    )
    
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name='分析时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'model_3d_analyses'
        verbose_name = '3D模型解析'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.part.part_number} - {self.file_format} - {self.status}"


class SurfaceZone(models.Model):
    """外观面区域 - 用于A/B/C级面分类"""
    ZONE_TYPE_CHOICES = [
        ('A', 'A级面 - 直接可见'),
        ('B', 'B级面 - 间接可见'),
        ('C', 'C级面 - 不可见'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='surface_zones', verbose_name='零件'
    )
    
    # 区域信息
    zone_id = models.CharField(max_length=50, verbose_name='区域编号')
    zone_type = models.CharField(
        max_length=1, choices=ZONE_TYPE_CHOICES,
        verbose_name='外观面等级'
    )
    description = models.TextField(verbose_name='表面描述')
    location = models.CharField(max_length=200, blank=True, verbose_name='位置说明')
    
    # 质量要求
    quality_requirements = models.JSONField(default=list, blank=True, verbose_name='质量要求')
    color_code = models.CharField(max_length=20, default='GREY', verbose_name='颜色代码')
    # GREEN=A级面, YELLOW=B级面, GREY=C级面
    
    # 面积信息
    estimated_area = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True, verbose_name='估计面积(mm²)'
    )
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'surface_zones'
        verbose_name = '外观面区域'
        verbose_name_plural = verbose_name
        ordering = ['zone_type', 'zone_id']
    
    def __str__(self):
        return f"{self.part.part_number} - {self.zone_id} ({self.get_zone_type_display()})"


class DrawingReview(models.Model):
    """图纸评审记录"""
    STATUS_CHOICES = [
        ('PASS', '通过'),
        ('WARNING', '警告'),
        ('FAIL', '不通过'),
        ('N/A', '不适用'),
    ]
    
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='drawing_reviews', verbose_name='零件'
    )
    
    # 翻译检查结果
    translation_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='N/A', verbose_name='翻译检查状态'
    )
    translation_result = models.JSONField(default=dict, blank=True, verbose_name='翻译检查结果')
    
    # 内控检查结果
    internal_control_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='N/A', verbose_name='内控检查状态'
    )
    internal_control_result = models.JSONField(default=dict, blank=True, verbose_name='内控检查结果')
    
    # 识图完整性检查结果
    completeness_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='N/A', verbose_name='识图完整性状态'
    )
    completeness_result = models.JSONField(default=dict, blank=True, verbose_name='识图完整性结果')
    
    # 技术标准识别结果
    technical_standards = models.JSONField(default=list, blank=True, verbose_name='技术标准列表')
    # 格式: [{'process_name': '工序', 'standard_code': '标准号', 'standard_name': '名称', ...}]
    
    # 零件信息提取
    extracted_part_info = models.JSONField(default=dict, blank=True, verbose_name='提取的零件信息')
    
    # 总体评审状态
    overall_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='N/A', verbose_name='总体状态'
    )
    overall_comments = models.TextField(blank=True, verbose_name='总体评审意见')
    
    # 评审人
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='评审人'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='评审时间')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'drawing_reviews'
        verbose_name = '图纸评审记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.part.part_number} - 图纸评审 - {self.overall_status}"


class StandardInterpretation(models.Model):
    """技术标准解读"""
    part = models.ForeignKey(
        Part, on_delete=models.CASCADE,
        related_name='standard_interpretations', verbose_name='零件'
    )
    drawing_review = models.ForeignKey(
        DrawingReview, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='standard_interpretations',
        verbose_name='关联图纸评审'
    )
    
    # 标准信息
    standard_code = models.CharField(max_length=100, verbose_name='标准编号')
    standard_name = models.CharField(max_length=200, verbose_name='标准名称')
    process_name = models.CharField(max_length=100, blank=True, verbose_name='适用工序')
    
    # 解读内容
    overview = models.TextField(blank=True, verbose_name='标准概述')
    key_parameters = models.JSONField(default=list, blank=True, verbose_name='关键参数')
    # 格式: [{'parameter': '参数名', 'requirement': '要求', 'unit': '单位', ...}]
    
    process_control_points = models.JSONField(default=list, blank=True, verbose_name='工艺控制要点')
    # 格式: [{'point': '控制点', 'requirement': '要求', 'method': '方法'}]
    
    common_issues = models.JSONField(default=list, blank=True, verbose_name='常见问题')
    # 格式: [{'issue': '问题', 'cause': '原因', 'prevention': '预防措施'}]
    
    internal_control_focus = models.JSONField(default=list, blank=True, verbose_name='内部控制重点')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'standard_interpretations'
        verbose_name = '技术标准解读'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.standard_code} - {self.standard_name}"


class InspectionSOPItem(models.Model):
    """检验SOP项目"""
    CATEGORY_CHOICES = [
        ('DIMENSION', '尺寸检验'),
        ('APPEARANCE', '外观检验'),
        ('PERFORMANCE', '性能检验'),
        ('IDENTIFICATION', '标识检验'),
    ]
    
    sop_document = models.ForeignKey(
        SOPDocument, on_delete=models.CASCADE,
        related_name='inspection_items', verbose_name='SOP文档'
    )
    
    # 项目信息
    item_no = models.CharField(max_length=50, verbose_name='项目编号')
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        verbose_name='检验类别'
    )
    inspection_object = models.CharField(max_length=200, verbose_name='检验对象')
    attribute = models.CharField(max_length=100, blank=True, verbose_name='属性')
    
    # 规格要求
    nominal_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='标称值'
    )
    upper_limit = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='上限'
    )
    lower_limit = models.DecimalField(
        max_digits=15, decimal_places=6,
        null=True, blank=True, verbose_name='下限'
    )
    unit = models.CharField(max_length=10, blank=True, verbose_name='单位')
    
    # 检验方法
    inspection_tool = models.CharField(max_length=100, blank=True, verbose_name='检验工具')
    inspection_method = models.CharField(max_length=200, blank=True, verbose_name='检验方法')
    sampling_ratio = models.CharField(max_length=50, default='100%', verbose_name='抽样比例')
    acceptance_criteria = models.TextField(blank=True, verbose_name='验收标准')
    
    # 外观检验特有
    surface_zone = models.ForeignKey(
        SurfaceZone, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='外观面区域'
    )
    
    # 关键特性
    is_key_characteristic = models.BooleanField(default=False, verbose_name='是否关键特性')
    
    sequence = models.PositiveIntegerField(default=0, verbose_name='顺序')
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'inspection_sop_items'
        verbose_name = '检验SOP项目'
        verbose_name_plural = verbose_name
        ordering = ['category', 'sequence', 'item_no']
    
    def __str__(self):
        return f"{self.item_no} - {self.inspection_object}"
