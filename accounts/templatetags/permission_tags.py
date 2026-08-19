"""
自定义模板过滤器和标签
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """从字典中获取项目"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def contains_action(permissions, action):
    """检查权限列表是否包含指定操作"""
    if not permissions:
        return False
    return action in permissions


@register.simple_tag
def has_module_permission(user, module, action):
    """检查用户是否有指定模块的权限"""
    if user.is_superuser:
        return True
    
    try:
        profile = user.profile
        for role in profile.roles.filter(is_active=True):
            if role.has_permission(module, action):
                return True
    except:
        pass
    
    return False


@register.simple_tag
def get_user_roles(user):
    """获取用户的角色列表"""
    try:
        profile = user.profile
        return profile.roles.filter(is_active=True)
    except:
        return []


@register.inclusion_tag('accounts/includes/permission_badge.html')
def permission_badge(module, action):
    """显示权限徽章"""
    action_colors = {
        'view': 'secondary',
        'add': 'info',
        'change': 'warning',
        'delete': 'danger',
        'submit': 'primary',
        'review': 'warning',
        'approve': 'success',
        'publish': 'success',
    }
    
    action_names = {
        'view': '查看',
        'add': '新增',
        'change': '编辑',
        'delete': '删除',
        'submit': '提交',
        'review': '审核',
        'approve': '批准',
        'publish': '发布',
    }
    
    return {
        'action': action,
        'action_name': action_names.get(action, action),
        'color': action_colors.get(action, 'secondary'),
    }
