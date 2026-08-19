"""
初始化演示数据脚本
运行命令: python manage.py shell < init_data.py
或: python manage.py shell
>>> exec(open('init_data.py').read())
"""

from django.contrib.auth.models import User
from accounts.models import UserProfile, Role
from parts.models import Part
from inspections.models import InspectionPlan, InspectionCharacteristic
from measurements.models import MeasurementBatch, MeasurementRecord
from reports.models import ReportTemplate, InspectionReport
from workflows.models import ApprovalWorkflow, ApprovalStep
from decimal import Decimal
from datetime import datetime

# 创建用户
print("创建用户...")
admin_user, _ = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@fai-system.com',
        'first_name': '系统',
        'last_name': '管理员',
        'is_staff': True,
        'is_superuser': True
    }
)
admin_user.set_password('admin123')
admin_user.save()

# 创建用户档案
admin_profile, _ = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={
        'employee_id': 'EMP00001',
        'department': '质量部',
        'position': '系统管理员'
    }
)

# 创建角色
print("创建角色...")
roles_data = [
    {
        'name': '检验员', 'code': 'INSPECTOR', 'description': '负责执行检验工作',
        'permissions': {
            'measurements': ['view', 'add', 'change', 'delete'],
            'inspections': ['view'],
        },
    },
    {
        'name': '审核员', 'code': 'REVIEWER', 'description': '负责审核检验数据',
        'permissions': {
            'inspections': ['view', 'review'],
            'reports': ['view', 'review'],
            'workflows': ['view'],
        },
    },
    {
        'name': '批准人', 'code': 'APPROVER', 'description': '负责批准检验报告',
        'permissions': {
            'reports': ['view', 'approve', 'publish'],
            'workflows': ['view', 'approve', 'reject'],
        },
    },
    {
        'name': '管理员', 'code': 'ADMIN', 'description': '系统管理员',
        'permissions': dict(Role.MODULE_PERMISSIONS),
    },
]

for role_data in roles_data:
    Role.objects.get_or_create(code=role_data['code'], defaults=role_data)

# 给admin用户分配角色
admin_profile.roles.add(Role.objects.get(code='ADMIN'))
admin_profile.roles.add(Role.objects.get(code='APPROVER'))

# 创建零件
print("创建零件...")
part1, _ = Part.objects.get_or_create(
    part_number='PN-2024-001',
    defaults={
        'part_name': '航空发动机叶片',
        'revision': 'A',
        'description': '钛合金高压压气机叶片',
        'material': 'TC4钛合金',
        'customer': '中国航空工业集团',
        'surface_treatment': '阳极氧化',
        'status': 'ACTIVE',
        'created_by': admin_user
    }
)

part2, _ = Part.objects.get_or_create(
    part_number='PN-2024-002',
    defaults={
        'part_name': '起落架支架',
        'revision': 'A',
        'description': '高强度钢制起落架支架',
        'material': '300M高强度钢',
        'customer': '中国商飞',
        'surface_treatment': '镀镉',
        'status': 'ACTIVE',
        'created_by': admin_user
    }
)

# 创建检验计划
print("创建检验计划...")
plan1, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-20240115-0001',
    defaults={
        'plan_name': '航空发动机叶片首件检验',
        'part': part1,
        'standard': 'AS9102',
        'sample_size': 3,
        'description': '首件检验，验证生产工艺能力',
        'status': 'ACTIVE',
        'created_by': admin_user,
        'approved_by': admin_user
    }
)

plan2, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-20240115-0002',
    defaults={
        'plan_name': '起落架支架首件检验',
        'part': part2,
        'standard': 'AS9102',
        'sample_size': 5,
        'description': '首件检验，验证热处理工艺',
        'status': 'PENDING_REVIEW',
        'created_by': admin_user
    }
)

# 创建检验特性
print("创建检验特性...")
chars_data = [
    {
        'char_number': 'DIM001',
        'char_name': '叶片长度',
        'char_type': 'DIMENSION',
        'nominal_value': Decimal('150.000'),
        'upper_tolerance': Decimal('0.100'),
        'lower_tolerance': Decimal('-0.100'),
        'measurement_method': 'CMM',
        'is_critical': True,
        'sequence': 1
    },
    {
        'char_number': 'DIM002',
        'char_name': '叶片宽度',
        'char_type': 'DIMENSION',
        'nominal_value': Decimal('50.000'),
        'upper_tolerance': Decimal('0.050'),
        'lower_tolerance': Decimal('-0.050'),
        'measurement_method': 'CMM',
        'is_critical': False,
        'sequence': 2
    },
    {
        'char_number': 'DIM003',
        'char_name': '安装孔直径',
        'char_type': 'DIMENSION',
        'nominal_value': Decimal('10.000'),
        'upper_tolerance': Decimal('0.015'),
        'lower_tolerance': Decimal('0.000'),
        'measurement_method': 'MECHANICAL',
        'is_critical': True,
        'sequence': 3
    },
    {
        'char_number': 'GD&T001',
        'char_name': '叶片轮廓度',
        'char_type': 'GD_T',
        'nominal_value': Decimal('0.000'),
        'upper_tolerance': Decimal('0.050'),
        'lower_tolerance': Decimal('-0.050'),
        'measurement_method': 'LASER',
        'is_critical': True,
        'sequence': 4
    },
]

for char_data in chars_data:
    InspectionCharacteristic.objects.get_or_create(
        plan=plan1,
        char_number=char_data['char_number'],
        defaults=char_data
    )

# 创建测量批次
print("创建测量批次...")
batch1, _ = MeasurementBatch.objects.get_or_create(
    batch_number='MB-20240115-001',
    defaults={
        'plan': plan1,
        'sample_size': 3,
        'equipment_type': 'CMM',
        'equipment_id': 'CMM-ZEISS-001',
        'equipment_name': 'Zeiss Contura G3',
        'environment_temp': Decimal('20.5'),
        'environment_humidity': Decimal('45.0'),
        'status': 'COMPLETED',
        'measured_by': admin_user,
        'measured_at': datetime.now()
    }
)

# 创建测量记录
print("创建测量记录...")
chars = plan1.characteristics.all()
sample_values = {
    'DIM001': [150.05, 149.98, 150.02],
    'DIM002': [50.02, 49.98, 50.01],
    'DIM003': [10.010, 10.008, 10.012],
    'GD&T001': [0.030, 0.028, 0.032],
}

for char in chars:
    if char.char_number in sample_values:
        for sample_idx, value in enumerate(sample_values[char.char_number], 1):
            MeasurementRecord.objects.get_or_create(
                batch=batch1,
                characteristic=char,
                sample_number=sample_idx,
                defaults={
                    'measured_value': Decimal(str(value))
                }
            )

# 创建统计分析（统一调用模型自带的calculate_all_statistics，避免与正式计算逻辑重复维护两份公式）
print("创建统计分析...")
batch1.calculate_all_statistics()

# 创建报告模板
print("创建报告模板...")
template1, _ = ReportTemplate.objects.get_or_create(
    name='AS9102标准模板',
    defaults={
        'standard': 'AS9102',
        'description': '符合AS9102航空航天标准的首件检验报告模板',
        'is_active': True,
        'created_by': admin_user
    }
)

# 创建检验报告
print("创建检验报告...")
report1, _ = InspectionReport.objects.get_or_create(
    report_number='FAI-RPT-2024-001',
    defaults={
        'plan': plan1,
        'batch': batch1,
        'template': template1,
        'title': '航空发动机叶片首件检验报告',
        'status': 'COMPLETED',
        'conclusion': 'PASS',
        'generated_by': admin_user
    }
)

# 创建审批工作流
print("创建审批工作流...")
workflow1, _ = ApprovalWorkflow.objects.get_or_create(
    workflow_type='PLAN_APPROVAL',
    plan=plan2,
    defaults={
        'status': 'IN_PROGRESS',
        'current_step': 1,
        'initiated_by': admin_user
    }
)

# 创建审批步骤
print("创建审批步骤...")
ApprovalStep.objects.get_or_create(
    workflow=workflow1,
    step_number=1,
    defaults={
        'step_name': 'REVIEW',
        'approver': admin_user,
        'status': 'PENDING'
    }
)

print("\n" + "="*50)
print("演示数据创建完成!")
print("="*50)
print(f"\n用户账号:")
print(f"  用户名: admin")
print(f"  密码: admin123")
print(f"\n零件数据: {Part.objects.count()} 个")
print(f"检验计划: {InspectionPlan.objects.count()} 个")
print(f"检验特性: {InspectionCharacteristic.objects.count()} 个")
print(f"测量批次: {MeasurementBatch.objects.count()} 个")
print(f"测量记录: {MeasurementRecord.objects.count()} 条")
print(f"检验报告: {InspectionReport.objects.count()} 个")
print(f"\n请访问系统查看演示数据!")
