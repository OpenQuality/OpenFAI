"""
账户应用信号
"""
import logging

logger = logging.getLogger(__name__)


def create_default_roles(sender, **kwargs):
    """创建默认角色"""
    from .models import Role
    
    default_roles = [
        {
            'name': '管理员',
            'code': 'ADMIN',
            'description': '系统管理员，拥有所有权限',
            'permissions': {
                'parts': ['view', 'add', 'change', 'delete'],
                'inspections': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve'],
                'measurements': ['view', 'add', 'change', 'delete'],
                'reports': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve', 'publish'],
                'workflows': ['view', 'add', 'change', 'delete', 'approve', 'reject'],
                'projects': ['view', 'add', 'change', 'delete', 'submit', 'review', 'approve'],
                'equipment': ['view', 'add', 'change', 'delete'],
                'users': ['view', 'add', 'change', 'delete'],
            }
        },
        {
            'name': '批准人',
            'code': 'APPROVER',
            'description': '可以批准提交的计划、报告和项目',
            'permissions': {
                'parts': ['view'],
                'inspections': ['view', 'review', 'approve'],
                'measurements': ['view'],
                'reports': ['view', 'review', 'approve', 'publish'],
                'workflows': ['view', 'approve', 'reject'],
                'projects': ['view', 'review', 'approve'],
                'equipment': ['view'],
            }
        },
        {
            'name': '审核员',
            'code': 'REVIEWER',
            'description': '负责审核提交的内容',
            'permissions': {
                'parts': ['view'],
                'inspections': ['view', 'review'],
                'measurements': ['view'],
                'reports': ['view', 'review'],
                'workflows': ['view'],
                'projects': ['view', 'review'],
                'equipment': ['view'],
            }
        },
        {
            'name': '检验员',
            'code': 'INSPECTOR',
            'description': '执行检验任务，可以添加测量数据',
            'permissions': {
                'parts': ['view'],
                'inspections': ['view'],
                'measurements': ['view', 'add', 'change'],
                'reports': ['view'],
                'equipment': ['view'],
            }
        },
        {
            'name': '质量工程师',
            'code': 'QUALITY_ENGINEER',
            'description': '负责质量技术工作，可以创建检验计划、生成报告',
            'permissions': {
                'parts': ['view', 'add', 'change'],
                'inspections': ['view', 'add', 'change', 'submit'],
                'measurements': ['view', 'add', 'change'],
                'reports': ['view', 'add', 'change', 'submit'],
                'workflows': ['view'],
                'projects': ['view', 'add', 'change', 'submit'],
                'equipment': ['view'],
            }
        },
        {
            'name': '质量经理',
            'code': 'QUALITY_MANAGER',
            'description': '质量部门负责人，具有审核、批准和发布报告的权限',
            'permissions': {
                'parts': ['view', 'change'],
                'inspections': ['view', 'change', 'review', 'approve'],
                'measurements': ['view', 'change'],
                'reports': ['view', 'change', 'review', 'approve', 'publish'],
                'workflows': ['view', 'approve', 'reject'],
                'projects': ['view', 'change', 'review', 'approve'],
                'equipment': ['view', 'change'],
            }
        },
        {
            'name': '查看者',
            'code': 'VIEWER',
            'description': '仅查看权限，不能进行任何修改操作',
            'permissions': {
                'parts': ['view'],
                'inspections': ['view'],
                'measurements': ['view'],
                'reports': ['view'],
                'workflows': ['view'],
                'projects': ['view'],
                'equipment': ['view'],
            }
        },
    ]
    
    for role_data in default_roles:
        role, created = Role.objects.get_or_create(
            code=role_data['code'],
            defaults={
                'name': role_data['name'],
                'description': role_data['description'],
                'permissions': role_data['permissions'],
                'is_active': True,
            }
        )
        if created:
            logger.info(f"创建默认角色: {role.name}")
        else:
            # 更新权限
            role.permissions = role_data['permissions']
            role.name = role_data['name']
            role.description = role_data['description']
            role.save()
            logger.info(f"更新角色权限: {role.name}")
