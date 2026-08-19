"""
Permission utilities for FAI System
"""
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps


def get_user_permissions(user):
    """
    获取用户的所有权限
    返回格式: {'parts': {'view': True, 'add': True, ...}, 'inspections': {...}, ...}
    """
    if not user.is_authenticated:
        return {}
    
    if user.is_superuser:
        # 超级用户拥有所有权限
        return {
            'parts': {'view': True, 'add': True, 'change': True, 'delete': True},
            'inspections': {'view': True, 'add': True, 'change': True, 'delete': True, 'submit': True, 'review': True, 'approve': True},
            'measurements': {'view': True, 'add': True, 'change': True, 'delete': True},
            'reports': {'view': True, 'add': True, 'change': True, 'delete': True, 'submit': True, 'review': True, 'approve': True, 'publish': True},
            'workflows': {'view': True, 'add': True, 'change': True, 'delete': True, 'approve': True, 'reject': True},
            'projects': {'view': True, 'add': True, 'change': True, 'delete': True, 'submit': True, 'review': True, 'approve': True},
            'equipment': {'view': True, 'add': True, 'change': True, 'delete': True},
            'users': {'view': True, 'add': True, 'change': True, 'delete': True},
        }
    
    permissions = {}
    try:
        profile = user.profile
        for role in profile.roles.filter(is_active=True):
            if role.permissions:
                for module, actions in role.permissions.items():
                    if module not in permissions:
                        permissions[module] = {}
                    for action in actions:
                        permissions[module][action] = True
    except:
        pass
    
    return permissions


def user_has_permission(user, module, action):
    """
    检查用户是否拥有指定模块的指定权限
    
    Args:
        user: 用户对象
        module: 模块名（如 'parts', 'inspections'）
        action: 操作名（如 'view', 'add', 'change', 'delete'）
    
    Returns:
        bool: 是否有权限
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    permissions = get_user_permissions(user)
    return permissions.get(module, {}).get(action, False)


def permission_required(module, action, redirect_url='dashboard'):
    """
    权限检查装饰器，用于视图函数
    
    用法:
        @permission_required('parts', 'add')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if user_has_permission(request.user, module, action):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f'您没有执行此操作的权限（{module}.{action}）')
            return redirect(redirect_url)
        return wrapper
    return decorator


class PermissionRequiredMixin:
    """
    权限检查混入类，用于类视图
    
    用法:
        class MyCreateView(PermissionRequiredMixin, CreateView):
            permission_module = 'parts'
            permission_action = 'add'
            ...
    """
    permission_module = None
    permission_action = None
    permission_redirect_url = 'dashboard'
    
    def dispatch(self, request, *args, **kwargs):
        # 超级用户跳过检查
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # 检查权限
        if self.permission_module and self.permission_action:
            if user_has_permission(request.user, self.permission_module, self.permission_action):
                return super().dispatch(request, *args, **kwargs)
            
            messages.error(request, f'您没有执行此操作的权限（{self.permission_module}.{self.permission_action}）')
            return redirect(self.permission_redirect_url)
        
        return super().dispatch(request, *args, **kwargs)


class AutoPermissionMixin:
    """
    自动权限检查混入类 - 根据视图类型自动判断权限
    
    CreateView -> add
    UpdateView -> change  
    DeleteView -> delete
    DetailView/ListView -> view
    """
    permission_module = None
    permission_redirect_url = 'dashboard'
    
    def get_permission_action(self):
        """根据视图类型自动判断权限操作"""
        from django.views.generic.edit import CreateView, UpdateView, DeleteView
        from django.views.generic.detail import DetailView
        from django.views.generic.list import ListView
        
        if isinstance(self, CreateView):
            return 'add'
        elif isinstance(self, UpdateView):
            return 'change'
        elif isinstance(self, DeleteView):
            return 'delete'
        elif isinstance(self, (DetailView, ListView)):
            return 'view'
        return 'view'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        if self.permission_module:
            action = self.get_permission_action()
            if user_has_permission(request.user, self.permission_module, action):
                return super().dispatch(request, *args, **kwargs)
            
            messages.error(request, f'您没有执行此操作的权限（{self.permission_module}.{action}）')
            return redirect(self.permission_redirect_url)
        
        return super().dispatch(request, *args, **kwargs)
