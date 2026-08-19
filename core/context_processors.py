"""
Core context processors for FAI System
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


def menu_permissions(request):
    """
    根据用户权限过滤菜单项
    无角色的用户不能访问任何菜单
    """
    # 检查用户是否有任何角色
    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            profile = request.user.profile
            # 如果用户没有角色，返回空菜单
            if not profile.roles.exists():
                return {
                    'filtered_menus': {},
                    'user_permissions': {}
                }
        except:
            # 如果用户没有profile，返回空菜单
            return {
                'filtered_menus': {},
                'user_permissions': {}
            }
    
    # 默认菜单结构
    all_menus = {
        'overview': {
            'title': '概览',
            'items': [
                {'name': '仪表盘', 'url': 'dashboard', 'icon': 'bi-speedometer2', 'module': 'dashboard', 'action': 'view'},
                {'name': '统计分析', 'url': 'statistics', 'icon': 'bi-bar-chart', 'module': 'dashboard', 'action': 'view'},
                {'name': '使用指南', 'url': 'help_guide', 'icon': 'bi-question-circle', 'no_permission_check': True},
            ]
        },
        'core_business': {
            'title': '核心业务',
            'items': [
                {'name': '项目管理', 'url': 'project_list', 'icon': 'bi-folder', 'module': 'projects', 'action': 'view'},
                {'name': '零件管理', 'url': 'part_list', 'icon': 'bi-box-seam', 'module': 'parts', 'action': 'view'},
                {'name': '检验计划', 'url': 'plan_list', 'icon': 'bi-clipboard-check', 'module': 'inspections', 'action': 'view'},
                {'name': '测量批次', 'url': 'batch_list', 'icon': 'bi-rulers', 'module': 'measurements', 'action': 'view'},
                {'name': 'Cp/Cpk分析', 'url': 'cpk_analysis', 'icon': 'bi-graph-up', 'module': 'measurements', 'action': 'view'},
                {'name': '检验报告', 'url': 'report_list', 'icon': 'bi-file-earmark-pdf', 'module': 'reports', 'action': 'view'},
            ]
        },
        'inspection_prep': {
            'title': '检验准备',
            'items': [
                {'name': 'SOP文档', 'url': 'sop_list', 'icon': 'bi-file-earmark-text', 'module': 'parts', 'action': 'view'},
                {'name': '控制要求', 'url': 'control_requirement_list', 'icon': 'bi-shield-plus', 'module': 'parts', 'action': 'view'},
                {'name': '风险点', 'url': 'risk_point_list', 'icon': 'bi-exclamation-circle', 'module': 'parts', 'action': 'view'},
            ]
        },
        'workflow': {
            'title': '流程管理',
            'items': [
                {'name': '审批流程', 'url': 'workflow_list', 'icon': 'bi-diagram-3', 'module': 'workflows', 'action': 'view'},
                {'name': '不合格品处理', 'url': 'ncr_list', 'icon': 'bi-exclamation-triangle', 'module': 'workflows', 'action': 'view'},
                {'name': '设备集成', 'url': 'equipment_list', 'icon': 'bi-cpu', 'module': 'equipment', 'action': 'view'},
            ]
        },
        'system': {
            'title': '系统管理',
            'items': [
                {'name': '引擎配置', 'url': 'ocr_engines', 'icon': 'bi-cpu', 'admin_only_item': True},
                {'name': '用户管理', 'url': 'user_list', 'icon': 'bi-people', 'module': 'users', 'action': 'view'},
                {'name': '角色管理', 'url': 'role_list', 'icon': 'bi-shield-check', 'module': 'users', 'action': 'view'},
                {'name': '后台管理', 'url': '/admin/', 'icon': 'bi-gear', 'is_external': True, 'admin_only_item': True},
                {'name': '退出登录', 'url': 'logout', 'icon': 'bi-box-arrow-left', 'no_permission_check': True},
            ],
            'admin_only': False
        }
    }
    
    # 获取用户权限
    user_permissions = get_user_permissions(request.user)
    is_admin = request.user.is_superuser or request.user.is_staff
    
    # 过滤菜单
    filtered_menus = {}
    for section_key, section in all_menus.items():
        # 系统管理只有管理员可见
        if section.get('admin_only') and not is_admin:
            continue
        
        filtered_items = []
        for item in section['items']:
            # 不需要权限检查的项（如退出登录）
            if item.get('no_permission_check'):
                filtered_items.append(item)
                continue
            
            # 仅管理员可见的项
            if item.get('admin_only_item') and not is_admin:
                continue
            
            # 如果没有权限要求或者是超管，直接添加
            if 'module' not in item or request.user.is_superuser:
                filtered_items.append(item)
                continue
            
            # 检查权限
            module = item.get('module')
            action = item.get('action', 'view')
            if user_permissions.get(module, {}).get(action, False):
                filtered_items.append(item)
        
        if filtered_items:
            filtered_menus[section_key] = {
                'title': section['title'],
                'items': filtered_items
            }
    
    return {
        'filtered_menus': filtered_menus,
        'user_permissions': user_permissions
    }


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


class ViewPermissionMixin:
    """
    视图权限混入类 - 根据视图类型自动判断权限
    
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
