from django.db import models
from django.contrib.auth.models import User
from core.models import BaseModel
import os


def signature_upload_path(instance, filename):
    """电子签名文件上传路径"""
    return f'signatures/{instance.user.username}/{filename}'


class Role(models.Model):
    """角色定义"""
    ROLE_CHOICES = [
        ('INSPECTOR', '检验员'),
        ('REVIEWER', '审核员'),
        ('APPROVER', '批准人'),
        ('ADMIN', '管理员'),
        ('QUALITY_ENGINEER', '质量工程师'),
        ('QUALITY_MANAGER', '质量经理'),
        ('VIEWER', '查看者'),
    ]
    
    # 模块权限定义
    MODULE_PERMISSIONS = {
        'parts': ['view', 'add', 'change', 'delete'],
        'inspections': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve'],
        'measurements': ['view', 'add', 'change', 'delete'],
        'reports': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve', 'publish'],
        'workflows': ['view', 'add', 'change', 'delete', 'approve', 'reject'],
        'projects': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve'],
        'equipment': ['view', 'add', 'change', 'delete'],
        'users': ['view', 'add', 'change', 'delete'],
    }
    
    name = models.CharField(max_length=50, unique=True, verbose_name='角色名称')
    code = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True, verbose_name='角色代码')
    description = models.TextField(blank=True, verbose_name='角色描述')
    permissions = models.JSONField(default=dict, blank=True, verbose_name='权限列表')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'accounts_roles'
        verbose_name = '角色'
        verbose_name_plural = verbose_name
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def has_permission(self, module, action):
        """检查是否拥有指定模块的指定权限"""
        if not self.permissions:
            return False
        module_perms = self.permissions.get(module, [])
        return action in module_perms
    
    def get_permissions_display(self):
        """获取权限的友好显示"""
        if not self.permissions:
            return "无权限"
        
        displays = []
        for module, actions in self.permissions.items():
            module_name = dict(
                parts='零件管理', inspections='检验计划', measurements='测量数据',
                reports='检验报告', workflows='审批流程', projects='项目管理',
                equipment='设备管理', users='用户管理'
            ).get(module, module)
            displays.append(f"{module_name}: {', '.join(actions)}")
        return '；'.join(displays)


class UserProfile(models.Model):
    """用户扩展信息 - 简化版，无审核字段"""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, 
        related_name='profile', verbose_name='用户'
    )
    employee_id = models.CharField(max_length=50, unique=True, verbose_name='工号')
    department = models.CharField(max_length=100, verbose_name='部门')
    position = models.CharField(max_length=100, verbose_name='职位')
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话')
    signature_image = models.ImageField(
        upload_to=signature_upload_path, 
        blank=True, null=True, verbose_name='电子签名图片'
    )
    roles = models.ManyToManyField(Role, blank=True, verbose_name='角色')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'accounts_profiles'
        verbose_name = '用户档案'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"
    
    def get_full_name(self):
        """获取完整姓名"""
        if self.user.first_name or self.user.last_name:
            return f"{self.user.last_name}{self.user.first_name}"
        return self.user.username
    
    def has_role(self, role_code):
        """检查是否拥有指定角色"""
        return self.roles.filter(code=role_code).exists()
    
    def is_approved(self):
        """兼容方法 - 简化版直接返回 True"""
        return True
    
    def has_any_permission(self):
        """检查用户是否有任何权限"""
        return self.roles.filter(is_active=True).exists()


class Department(models.Model):
    """部门"""
    name = models.CharField(max_length=100, unique=True, verbose_name='部门名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='部门代码')
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True, verbose_name='部门经理'
    )
    description = models.TextField(blank=True, verbose_name='部门描述')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, 
        null=True, blank=True, verbose_name='上级部门'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'accounts_departments'
        verbose_name = '部门'
        verbose_name_plural = verbose_name
        ordering = ['name']
    
    def __str__(self):
        return self.name


class UserActivity(models.Model):
    """用户活动记录"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='activities', verbose_name='用户'
    )
    activity_type = models.CharField(max_length=50, verbose_name='活动类型')
    description = models.TextField(verbose_name='活动描述')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='活动时间')
    
    class Meta:
        db_table = 'accounts_activities'
        verbose_name = '用户活动'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"
