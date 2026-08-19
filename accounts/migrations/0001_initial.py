# 初始迁移 - 干净版本，无审核字段
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import accounts.models


class Migration(migrations.Migration):
    initial = True
    
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='角色名称')),
                ('code', models.CharField(choices=[('INSPECTOR', '检验员'), ('REVIEWER', '审核员'), ('APPROVER', '批准人'), ('ADMIN', '管理员'), ('QUALITY_ENGINEER', '质量工程师'), ('QUALITY_MANAGER', '质量经理'), ('VIEWER', '查看者')], max_length=20, unique=True, verbose_name='角色代码')),
                ('description', models.TextField(blank=True, verbose_name='角色描述')),
                ('permissions', models.JSONField(blank=True, default=dict, verbose_name='权限列表')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '角色',
                'verbose_name_plural': '角色',
                'db_table': 'accounts_roles',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='部门名称')),
                ('code', models.CharField(max_length=20, unique=True, verbose_name='部门代码')),
                ('description', models.TextField(blank=True, verbose_name='部门描述')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='部门经理')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.department', verbose_name='上级部门')),
            ],
            options={
                'verbose_name': '部门',
                'verbose_name_plural': '部门',
                'db_table': 'accounts_departments',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(max_length=50, verbose_name='活动类型')),
                ('description', models.TextField(verbose_name='活动描述')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='活动时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户活动',
                'verbose_name_plural': '用户活动',
                'db_table': 'accounts_activities',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_id', models.CharField(max_length=50, unique=True, verbose_name='工号')),
                ('department', models.CharField(max_length=100, verbose_name='部门')),
                ('position', models.CharField(max_length=100, verbose_name='职位')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='电话')),
                ('signature_image', models.ImageField(blank=True, null=True, upload_to=accounts.models.signature_upload_path, verbose_name='电子签名图片')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('roles', models.ManyToManyField(blank=True, to='accounts.role', verbose_name='角色')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户档案',
                'verbose_name_plural': '用户档案',
                'db_table': 'accounts_profiles',
            },
        ),
    ]
