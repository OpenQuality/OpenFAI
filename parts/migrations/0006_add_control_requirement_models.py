# Generated migration for control requirements and SOP documents
# 兼容 SQLite 和 PostgreSQL

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    atomic = False  # 禁用事务

    dependencies = [
        ('parts', '0005_add_dimension_template'),
    ]

    operations = [
        # 添加3D模型文件字段到Part模型（SQLite兼容方式）
        migrations.AddField(
            model_name='part',
            name='model_3d_file',
            field=models.FileField(blank=True, help_text='支持解析。格式: STEP(.stp/.step), IGES(.igs/.iges), STL, OBJ, PLY', null=True, upload_to='models_3d/', verbose_name='3D模型文件'),
        ),
        migrations.AddField(
            model_name='part',
            name='model_3d_file_type',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='3D模型文件类型'),
        ),

        # 创建控制要求模型
        migrations.CreateModel(
            name='ControlRequirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requirement_id', models.CharField(max_length=50, verbose_name='要求编号')),
                ('requirement_name', models.CharField(max_length=200, verbose_name='要求名称')),
                ('control_type', models.CharField(choices=[('DIMENSION', '尺寸控制'), ('SURFACE', '表面质量'), ('MATERIAL', '材料要求'), ('GEOMETRY', '形位公差'), ('PROCESS', '工艺要求'), ('ASSEMBLY', '装配要求'), ('SAFETY', '安全要求'), ('OTHER', '其他')], max_length=20, verbose_name='控制类型')),
                ('description', models.TextField(verbose_name='要求描述')),
                ('nominal_value', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='标称值')),
                ('upper_limit', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='上限')),
                ('lower_limit', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='下限')),
                ('unit', models.CharField(blank=True, max_length=10, verbose_name='单位')),
                ('risk_level', models.CharField(choices=[('HIGH', '高风险'), ('MEDIUM', '中风险'), ('LOW', '低风险')], default='MEDIUM', max_length=10, verbose_name='风险等级')),
                ('risk_factors', models.JSONField(blank=True, default=list, verbose_name='风险因素')),
                ('impact_analysis', models.TextField(blank=True, verbose_name='影响分析')),
                ('inspection_method', models.CharField(blank=True, max_length=200, verbose_name='检测方法')),
                ('inspection_tool', models.CharField(blank=True, max_length=200, verbose_name='检测工具')),
                ('inspection_frequency', models.CharField(blank=True, max_length=100, verbose_name='检测频次')),
                ('is_key_characteristic', models.BooleanField(default=False, verbose_name='是否关键特性')),
                ('is_safety_critical', models.BooleanField(default=False, verbose_name='是否安全关键')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='control_requirements', to='parts.part', verbose_name='零件')),
            ],
            options={
                'verbose_name': '控制要求',
                'verbose_name_plural': '控制要求',
                'db_table': 'control_requirements',
                'ordering': ['requirement_id'],
            },
        ),

        # 创建关键风险点模型
        migrations.CreateModel(
            name='RiskPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('risk_id', models.CharField(max_length=50, verbose_name='风险编号')),
                ('risk_name', models.CharField(max_length=200, verbose_name='风险名称')),
                ('description', models.TextField(verbose_name='风险描述')),
                ('risk_category', models.CharField(blank=True, max_length=100, verbose_name='风险类别')),
                ('severity', models.CharField(choices=[('CRITICAL', '严重'), ('MAJOR', '重要'), ('MINOR', '次要')], default='MAJOR', max_length=20, verbose_name='严重程度')),
                ('probability', models.DecimalField(decimal_places=2, default=0.5, max_digits=3, verbose_name='发生概率')),
                ('affected_dimensions', models.JSONField(blank=True, default=list, verbose_name='影响尺寸')),
                ('affected_processes', models.JSONField(blank=True, default=list, verbose_name='影响工序')),
                ('prevention_measures', models.TextField(blank=True, verbose_name='预防措施')),
                ('correction_measures', models.TextField(blank=True, verbose_name='纠正措施')),
                ('contingency_plan', models.TextField(blank=True, verbose_name='应急预案')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='risk_points', to='parts.part', verbose_name='零件')),
            ],
            options={
                'verbose_name': '关键风险点',
                'verbose_name_plural': '关键风险点',
                'db_table': 'risk_points',
                'ordering': ['-severity', 'risk_id'],
            },
        ),

        # 创建SOP文档模型
        migrations.CreateModel(
            name='SOPDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_number', models.CharField(max_length=100, unique=True, verbose_name='文档编号')),
                ('document_title', models.CharField(max_length=200, verbose_name='文档标题')),
                ('document_type', models.CharField(choices=[('SOP', '标准操作程序'), ('WORK_INSTRUCTION', '作业指导书'), ('INSPECTION_GUIDE', '检验指导书'), ('CONTROL_PLAN', '控制计划'), ('INTERNAL_GUIDE', '内部建议指导书')], default='SOP', max_length=30, verbose_name='文档类型')),
                ('version', models.CharField(default='1.0', max_length=20, verbose_name='版本号')),
                ('content', models.TextField(verbose_name='文档内容')),
                ('sections', models.JSONField(blank=True, default=list, verbose_name='章节结构')),
                ('status', models.CharField(choices=[('DRAFT', '草稿'), ('REVIEW', '审核中'), ('APPROVED', '已批准'), ('PUBLISHED', '已发布'), ('OBSOLETE', '已作废')], default='DRAFT', max_length=20, verbose_name='状态')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='审核时间')),
                ('approved_at', models.DateTimeField(blank=True, null=True, verbose_name='批准时间')),
                ('effective_date', models.DateField(blank=True, null=True, verbose_name='生效日期')),
                ('expiry_date', models.DateField(blank=True, null=True, verbose_name='失效日期')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sop_documents', to='parts.part', verbose_name='零件')),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_sop_documents', to=settings.AUTH_USER_MODEL, verbose_name='批准人')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sop_documents', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_sop_documents', to=settings.AUTH_USER_MODEL, verbose_name='审核人')),
            ],
            options={
                'verbose_name': 'SOP文档',
                'verbose_name_plural': 'SOP文档',
                'db_table': 'sop_documents',
                'ordering': ['-created_at'],
            },
        ),

        # 创建3D模型解析结果模型
        migrations.CreateModel(
            name='Model3DAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PENDING', '待解析'), ('PROCESSING', '解析中'), ('COMPLETED', '已完成'), ('FAILED', '失败')], default='PENDING', max_length=20, verbose_name='状态')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('file_format', models.CharField(max_length=20, verbose_name='文件格式')),
                ('file_size', models.PositiveIntegerField(default=0, verbose_name='文件大小(字节)')),
                ('vertex_count', models.PositiveIntegerField(default=0, verbose_name='顶点数量')),
                ('face_count', models.PositiveIntegerField(default=0, verbose_name='面数量')),
                ('edge_count', models.PositiveIntegerField(default=0, verbose_name='边数量')),
                ('bounding_box', models.JSONField(blank=True, default=dict, verbose_name='边界框')),
                ('volume', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='体积(mm³)')),
                ('surface_area', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='表面积(mm²)')),
                ('geometry_data', models.JSONField(blank=True, default=dict, verbose_name='几何数据')),
                ('mesh_data', models.JSONField(blank=True, default=dict, verbose_name='网格数据')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='元数据')),
                ('features', models.JSONField(blank=True, default=list, verbose_name='提取特征')),
                ('analyzed_at', models.DateTimeField(blank=True, null=True, verbose_name='分析时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='model_3d_analyses', to='parts.part', verbose_name='零件')),
            ],
            options={
                'verbose_name': '3D模型解析',
                'verbose_name_plural': '3D模型解析',
                'db_table': 'model_3d_analyses',
                'ordering': ['-created_at'],
            },
        ),

        # 添加外键关系
        migrations.AddField(
            model_name='controlrequirement',
            name='extraction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='control_requirements', to='parts.cadextraction', verbose_name='关联解析记录'),
        ),
        migrations.AddField(
            model_name='controlrequirement',
            name='related_dimension',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='parts.dimension', verbose_name='关联尺寸'),
        ),
        migrations.AddField(
            model_name='sopdocument',
            name='extraction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sop_documents', to='parts.cadextraction', verbose_name='关联解析记录'),
        ),

        # 添加多对多关系
        migrations.AddField(
            model_name='riskpoint',
            name='related_requirements',
            field=models.ManyToManyField(blank=True, related_name='risk_points', to='parts.ControlRequirement', verbose_name='关联控制要求'),
        ),
        migrations.AddField(
            model_name='sopdocument',
            name='control_requirements',
            field=models.ManyToManyField(blank=True, related_name='sop_documents', to='parts.ControlRequirement', verbose_name='控制要求'),
        ),
        migrations.AddField(
            model_name='sopdocument',
            name='risk_points',
            field=models.ManyToManyField(blank=True, related_name='sop_documents', to='parts.RiskPoint', verbose_name='风险点'),
        ),
        migrations.AddField(
            model_name='model3danalysis',
            name='extracted_dimensions',
            field=models.ManyToManyField(blank=True, related_name='model_3d_analyses', to='parts.Dimension', verbose_name='提取尺寸'),
        ),
    ]
