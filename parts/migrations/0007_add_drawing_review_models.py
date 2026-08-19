# Generated migration for drawing review and surface zone models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parts', '0006_add_control_requirement_models'),
    ]

    operations = [
        # 创建外观面区域模型
        migrations.CreateModel(
            name='SurfaceZone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('zone_id', models.CharField(max_length=50, verbose_name='区域编号')),
                ('zone_type', models.CharField(choices=[('A', 'A级面 - 直接可见'), ('B', 'B级面 - 间接可见'), ('C', 'C级面 - 不可见')], max_length=1, verbose_name='外观面等级')),
                ('description', models.TextField(verbose_name='表面描述')),
                ('location', models.CharField(blank=True, max_length=200, verbose_name='位置说明')),
                ('quality_requirements', models.JSONField(blank=True, default=list, verbose_name='质量要求')),
                ('color_code', models.CharField(default='GREY', max_length=20, verbose_name='颜色代码')),
                ('estimated_area', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='估计面积(mm²)')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='surface_zones', to='parts.part', verbose_name='零件')),
            ],
            options={
                'verbose_name': '外观面区域',
                'verbose_name_plural': '外观面区域',
                'db_table': 'surface_zones',
                'ordering': ['zone_type', 'zone_id'],
            },
        ),
        
        # 创建图纸评审记录模型
        migrations.CreateModel(
            name='DrawingReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('translation_status', models.CharField(choices=[('PASS', '通过'), ('WARNING', '警告'), ('FAIL', '不通过'), ('N/A', '不适用')], default='N/A', max_length=20, verbose_name='翻译检查状态')),
                ('translation_result', models.JSONField(blank=True, default=dict, verbose_name='翻译检查结果')),
                ('internal_control_status', models.CharField(choices=[('PASS', '通过'), ('WARNING', '警告'), ('FAIL', '不通过'), ('N/A', '不适用')], default='N/A', max_length=20, verbose_name='内控检查状态')),
                ('internal_control_result', models.JSONField(blank=True, default=dict, verbose_name='内控检查结果')),
                ('completeness_status', models.CharField(choices=[('PASS', '通过'), ('WARNING', '警告'), ('FAIL', '不通过'), ('N/A', '不适用')], default='N/A', max_length=20, verbose_name='识图完整性状态')),
                ('completeness_result', models.JSONField(blank=True, default=dict, verbose_name='识图完整性结果')),
                ('technical_standards', models.JSONField(blank=True, default=list, verbose_name='技术标准列表')),
                ('extracted_part_info', models.JSONField(blank=True, default=dict, verbose_name='提取的零件信息')),
                ('overall_status', models.CharField(choices=[('PASS', '通过'), ('WARNING', '警告'), ('FAIL', '不通过'), ('N/A', '不适用')], default='N/A', max_length=20, verbose_name='总体状态')),
                ('overall_comments', models.TextField(blank=True, verbose_name='总体评审意见')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='评审时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drawing_reviews', to='parts.part', verbose_name='零件')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='评审人')),
            ],
            options={
                'verbose_name': '图纸评审记录',
                'verbose_name_plural': '图纸评审记录',
                'db_table': 'drawing_reviews',
                'ordering': ['-created_at'],
            },
        ),
        
        # 创建技术标准解读模型
        migrations.CreateModel(
            name='StandardInterpretation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('standard_code', models.CharField(max_length=100, verbose_name='标准编号')),
                ('standard_name', models.CharField(max_length=200, verbose_name='标准名称')),
                ('process_name', models.CharField(blank=True, max_length=100, verbose_name='适用工序')),
                ('overview', models.TextField(blank=True, verbose_name='标准概述')),
                ('key_parameters', models.JSONField(blank=True, default=list, verbose_name='关键参数')),
                ('process_control_points', models.JSONField(blank=True, default=list, verbose_name='工艺控制要点')),
                ('common_issues', models.JSONField(blank=True, default=list, verbose_name='常见问题')),
                ('internal_control_focus', models.JSONField(blank=True, default=list, verbose_name='内部控制重点')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('drawing_review', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='standard_interpretations', to='parts.drawingreview', verbose_name='关联图纸评审')),
                ('part', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='standard_interpretations', to='parts.part', verbose_name='零件')),
            ],
            options={
                'verbose_name': '技术标准解读',
                'verbose_name_plural': '技术标准解读',
                'db_table': 'standard_interpretations',
                'ordering': ['-created_at'],
            },
        ),
        
        # 创建检验SOP项目模型
        migrations.CreateModel(
            name='InspectionSOPItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_no', models.CharField(max_length=50, verbose_name='项目编号')),
                ('category', models.CharField(choices=[('DIMENSION', '尺寸检验'), ('APPEARANCE', '外观检验'), ('PERFORMANCE', '性能检验'), ('IDENTIFICATION', '标识检验')], max_length=20, verbose_name='检验类别')),
                ('inspection_object', models.CharField(max_length=200, verbose_name='检验对象')),
                ('attribute', models.CharField(blank=True, max_length=100, verbose_name='属性')),
                ('nominal_value', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='标称值')),
                ('upper_limit', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='上限')),
                ('lower_limit', models.DecimalField(blank=True, decimal_places=6, max_digits=15, null=True, verbose_name='下限')),
                ('unit', models.CharField(blank=True, max_length=10, verbose_name='单位')),
                ('inspection_tool', models.CharField(blank=True, max_length=100, verbose_name='检验工具')),
                ('inspection_method', models.CharField(blank=True, max_length=200, verbose_name='检验方法')),
                ('sampling_ratio', models.CharField(default='100%', max_length=50, verbose_name='抽样比例')),
                ('acceptance_criteria', models.TextField(blank=True, verbose_name='验收标准')),
                ('is_key_characteristic', models.BooleanField(default=False, verbose_name='是否关键特性')),
                ('sequence', models.PositiveIntegerField(default=0, verbose_name='顺序')),
                ('notes', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('sop_document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspection_items', to='parts.sopdocument', verbose_name='SOP文档')),
                ('surface_zone', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='parts.surfacezone', verbose_name='外观面区域')),
            ],
            options={
                'verbose_name': '检验SOP项目',
                'verbose_name_plural': '检验SOP项目',
                'db_table': 'inspection_sop_items',
                'ordering': ['category', 'sequence', 'item_no'],
            },
        ),
    ]
