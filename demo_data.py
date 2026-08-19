"""
全流程演示数据生成脚本
覆盖：用户、零件、FAI项目、SOP、检验计划、测量数据、Cpk统计、检验报告、审批流程、NCR

运行方式:
    python manage.py shell < demo_data.py
"""

import math
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import UserProfile, Role
from parts.models import Part, SOPDocument, InspectionSOPItem
from inspections.models import InspectionPlan, InspectionCharacteristic
from measurements.models import MeasurementBatch, MeasurementRecord
from reports.models import ReportTemplate, InspectionReport, MaterialCertification, SpecialProcessRecord
from workflows.models import ApprovalWorkflow, ApprovalStep, NonConformanceReport, NonConformanceAction
from core.models import FAIProject, ProjectStep

print("=" * 60)
print("OpenFAI 演示数据生成")
print("=" * 60)

# ─────────────────────────────────────────────
# 1. 用户与角色
# ─────────────────────────────────────────────
print("\n[1/10] 创建用户和角色...")


def make_user(username, first_name, last_name, email, emp_id, dept, pos, pw='demo123', staff=False):
    u, _ = User.objects.get_or_create(
        username=username,
        defaults={'first_name': first_name, 'last_name': last_name,
                  'email': email, 'is_staff': staff, 'is_superuser': staff}
    )
    u.set_password(pw)
    u.save()
    UserProfile.objects.get_or_create(
        user=u,
        defaults={'employee_id': emp_id, 'department': dept, 'position': pos}
    )
    return u


admin_user = make_user('admin', '系统', '管理员', 'admin@fai-system.com',
                        'EMP00001', '质量部', '系统管理员', pw='admin123', staff=True)
inspector1 = make_user('inspector1', '明', '王', 'wang.ming@fai.com',
                        'EMP00101', '质量部', '质量检验员')
reviewer1  = make_user('reviewer1',  '华', '李', 'li.hua@fai.com',
                        'EMP00201', '质量部', '质量审核员')
approver1  = make_user('approver1',  '总', '张', 'zhang.zong@fai.com',
                        'EMP00301', '质量部', '质量经理')
engineer1  = make_user('engineer1',  '工', '刘', 'liu.gong@fai.com',
                        'EMP00401', '工程部', '质量工程师')

roles_data = [
    {'name': '检验员',     'code': 'INSPECTOR',       'description': '负责执行检验工作',
     'permissions': {'measurements': ['view', 'add', 'change', 'delete'], 'inspections': ['view']}},
    {'name': '审核员',     'code': 'REVIEWER',        'description': '负责审核检验数据',
     'permissions': {'inspections': ['view', 'review'], 'reports': ['view', 'review'], 'workflows': ['view']}},
    {'name': '批准人',     'code': 'APPROVER',        'description': '负责批准检验报告',
     'permissions': {'reports': ['view', 'approve', 'publish'], 'workflows': ['view', 'approve', 'reject']}},
    {'name': '质量工程师', 'code': 'QUALITY_ENGINEER','description': '质量工程师',
     'permissions': {'inspections': ['view', 'add', 'change'], 'measurements': ['view', 'add', 'change'], 'reports': ['view']}},
    {'name': '管理员',     'code': 'ADMIN',           'description': '系统管理员',
     'permissions': dict(Role.MODULE_PERMISSIONS)},
]
for rd in roles_data:
    Role.objects.get_or_create(code=rd['code'], defaults=rd)

for user, codes in [
    (admin_user, ['ADMIN', 'APPROVER']),
    (inspector1, ['INSPECTOR']),
    (reviewer1,  ['REVIEWER']),
    (approver1,  ['APPROVER']),
    (engineer1,  ['QUALITY_ENGINEER']),
]:
    profile = UserProfile.objects.get(user=user)
    for code in codes:
        profile.roles.add(Role.objects.get(code=code))

# ─────────────────────────────────────────────
# 2. 零件
# ─────────────────────────────────────────────
print("[2/10] 创建零件...")

parts_raw = [
    dict(part_number='PN-2026-001', part_name='航空发动机压气机叶片', revision='C',
         description='高压压气机第3级叶片，钛合金，用于某型涡扇发动机。',
         material='TC4钛合金 (Ti-6Al-4V)', weight=Decimal('0.235'),
         surface_treatment='阳极氧化 + 热障涂层',
         customer='中国航空工业集团', customer_part_number='AVIC-B3-2026-001',
         order_number='PO-2026-0321', production_quantity=100, fai_quantity=3,
         department='精密加工车间', operator='王明', status='ACTIVE'),
    dict(part_number='PN-2026-002', part_name='液压系统控制阀体', revision='B',
         description='飞机起落架液压系统四通换向阀阀体，铝合金精密加工。',
         material='7075-T6铝合金', weight=Decimal('1.820'),
         surface_treatment='硬质阳极氧化',
         customer='中国商飞', customer_part_number='COMAC-HYD-7788',
         order_number='PO-2026-0589', production_quantity=50, fai_quantity=5,
         department='铸造分厂', operator='刘工', status='ACTIVE'),
    dict(part_number='PN-2026-003', part_name='直升机传动系统输出轴', revision='A',
         description='主减速器输出端传动轴，42CrMo调质处理，表面感应淬火。',
         material='42CrMo合金钢', weight=Decimal('3.450'),
         surface_treatment='感应淬火 + 发黑处理',
         customer='中航直升机', customer_part_number='AVIC-HEL-SHAFT-05',
         order_number='PO-2026-0712', production_quantity=20, fai_quantity=3,
         department='锻造车间', operator='张总', status='ACTIVE'),
    dict(part_number='PN-2026-004', part_name='卫星平台主承力框架', revision='A',
         description='小型遥感卫星主承力结构件，碳纤维复合材料，承受发射过载。',
         material='T800级碳纤维/环氧树脂复合材料', weight=Decimal('0.680'),
         surface_treatment='防静电涂层',
         customer='航天科技集团', customer_part_number='CASC-SAT-FRAME-12',
         order_number='PO-2026-0890', production_quantity=5, fai_quantity=1,
         department='复合材料车间', operator='刘工', status='DRAFT'),
]

parts = []
for pd in parts_raw:
    p, _ = Part.objects.get_or_create(
        part_number=pd['part_number'],
        defaults={**pd, 'created_by': admin_user}
    )
    parts.append(p)

part1, part2, part3, part4 = parts

# ─────────────────────────────────────────────
# 3. SOP文档
# ─────────────────────────────────────────────
print("[3/10] 创建SOP文档...")

CONTENT_BLADE = """1. 目的
本检验指导书规定了压气机叶片（PN-2026-001）的检验要求、方法和判定准则。

2. 适用范围
适用于PN-2026-001 Rev.C叶片的首件检验（FAI）和过程检验。

3. 检验设备
- 三坐标测量机（CMM）：Zeiss Contura G3
- 激光轮廓仪
- 粗糙度测量仪：TIME TR200
- 气动量仪（安装孔）

4. 检验环境
温度：20±2℃；湿度：45±10%RH。检验前工件充分清洁，去除切削液。

5. 关键特性检验要求
(1) 叶片弦长：85.0±0.1mm，CMM测量，全检
(2) 最大厚度：12.5±0.05mm，CMM测量，全检
(3) 安装孔径：Φ10 +0.015/0，气动量仪
(4) 叶身轮廓度：≤0.05mm，CMM逐点扫描
(5) 表面粗糙度Ra：≤0.8μm（气动面）

6. 不合格处置
超差工件贴红色标签，隔离，填写NCR报告。"""

CONTENT_HYDRAULIC = """1. 目的
规定液压控制阀体（PN-2026-002）的首件检验标准操作程序。

2. 关键特性
(1) 阀孔直径：Φ25 +0.021/0，气动量仪全检
(2) 阀体外径：Φ80±0.05mm，外径千分尺
(3) 密封槽宽度：3.2 -0/-0.03mm，精密卡尺
(4) 螺孔位置度：Φ0.1，CMM测量

3. 液压测试
安装到液压测试台，200bar保压5分钟，检查密封性。

4. 表面要求
内孔面Ra≤1.6μm；密封槽底面Ra≤0.8μm。"""

CONTENT_SHAFT = """1. 目的
规定直升机传动输出轴（PN-2026-003）的检验控制计划。

2. 关键特性
(1) 轴颈直径：Φ60 -0.012/-0.028mm（配合公差）
(2) 轴总长：380±0.2mm
(3) 花键大径：Φ72 +0.025/0
(4) 圆柱度：≤0.005mm（主轴颈）

3. 探伤要求
磁粉探伤（MT）：按MIL-STD-1949，不允许线性显示。"""

sop_list = [
    dict(document_number='SOP-QC-2026-001',
         document_title='航空发动机压气机叶片检验指导书',
         document_type='INSPECTION_GUIDE', version='3.0',
         content=CONTENT_BLADE, status='PUBLISHED',
         part=part1, effective_date=date(2026,1,15), expiry_date=date(2027,1,14)),
    dict(document_number='SOP-QC-2026-002',
         document_title='液压控制阀体首件检验SOP',
         document_type='SOP', version='2.1',
         content=CONTENT_HYDRAULIC, status='APPROVED',
         part=part2, effective_date=date(2026,3,1), expiry_date=date(2027,2,28)),
    dict(document_number='SOP-QC-2026-003',
         document_title='直升机传动轴检验控制计划',
         document_type='CONTROL_PLAN', version='1.0',
         content=CONTENT_SHAFT, status='REVIEW',
         part=part3, effective_date=None, expiry_date=None),
]

sop_docs = []
for sd in sop_list:
    is_approved = sd['status'] in ('APPROVED', 'PUBLISHED')
    doc, _ = SOPDocument.objects.get_or_create(
        document_number=sd['document_number'],
        defaults={
            'document_title': sd['document_title'],
            'document_type':  sd['document_type'],
            'version':        sd['version'],
            'content':        sd['content'],
            'status':         sd['status'],
            'part':           sd['part'],
            'effective_date': sd['effective_date'],
            'expiry_date':    sd['expiry_date'],
            'created_by':     admin_user,
            'reviewed_by':    reviewer1  if is_approved else None,
            'approved_by':    approver1  if is_approved else None,
            'reviewed_at':    timezone.now() - timedelta(days=5) if is_approved else None,
            'approved_at':    timezone.now() - timedelta(days=3) if is_approved else None,
        }
    )
    sop_docs.append(doc)

sop1, sop2, sop3 = sop_docs

# SOP检验项目（叶片）
sop_items = [
    dict(item_no='D-001', category='DIMENSION', inspection_object='叶片弦长',
         nominal_value=Decimal('85.0'), upper_limit=Decimal('85.1'), lower_limit=Decimal('84.9'),
         unit='mm', inspection_tool='CMM', inspection_method='三坐标测量',
         sampling_ratio='100%', is_key_characteristic=True, sequence=1),
    dict(item_no='D-002', category='DIMENSION', inspection_object='叶片最大厚度',
         nominal_value=Decimal('12.5'), upper_limit=Decimal('12.55'), lower_limit=Decimal('12.45'),
         unit='mm', inspection_tool='CMM', inspection_method='三坐标测量',
         sampling_ratio='100%', is_key_characteristic=True, sequence=2),
    dict(item_no='D-003', category='DIMENSION', inspection_object='安装孔径',
         nominal_value=Decimal('10.0'), upper_limit=Decimal('10.015'), lower_limit=Decimal('10.0'),
         unit='mm', inspection_tool='气动量仪', inspection_method='气动量仪测量',
         sampling_ratio='100%', is_key_characteristic=True, sequence=3),
    dict(item_no='G-001', category='DIMENSION', inspection_object='叶身轮廓度',
         nominal_value=Decimal('0.0'), upper_limit=Decimal('0.05'), lower_limit=None,
         unit='mm', inspection_tool='激光轮廓仪', inspection_method='激光扫描',
         sampling_ratio='100%', is_key_characteristic=True, sequence=4),
    dict(item_no='A-001', category='APPEARANCE', inspection_object='外观检验',
         nominal_value=None, upper_limit=None, lower_limit=None,
         unit='', inspection_tool='目视', inspection_method='目视检查',
         acceptance_criteria='无毛刺、裂纹、磕碰伤，涂层均匀无脱落',
         sampling_ratio='100%', is_key_characteristic=False, sequence=5),
]
for si in sop_items:
    InspectionSOPItem.objects.get_or_create(
        sop_document=sop1, item_no=si['item_no'],
        defaults={k: v for k, v in si.items() if k != 'item_no'}
    )

# ─────────────────────────────────────────────
# 4. 检验计划 & 检验特性
# ─────────────────────────────────────────────
print("[4/10] 创建检验计划和检验特性...")

plan1, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-2026-0001',
    defaults=dict(plan_name='压气机叶片首件检验计划', part=part1, standard='AS9102',
                  sample_size=10, description='高压压气机叶片首件检验，验证精密加工工艺能力。',
                  status='COMPLETED', created_by=admin_user,
                  approved_by=approver1, approved_at=timezone.now()-timedelta(days=30)))

plan2, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-2026-0002',
    defaults=dict(plan_name='液压控制阀体首件检验计划', part=part2, standard='AS9102',
                  sample_size=5, description='液压四通换向阀阀体首件检验，重点验证阀孔及密封槽。',
                  status='ACTIVE', created_by=admin_user,
                  approved_by=approver1, approved_at=timezone.now()-timedelta(days=10)))

plan3, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-2026-0003',
    defaults=dict(plan_name='直升机传动轴首件检验计划', part=part3, standard='AS9102',
                  sample_size=3, description='主减速器输出轴首件检验，关注轴颈精度和花键尺寸。',
                  status='IN_PROGRESS', created_by=engineer1))

plan4, _ = InspectionPlan.objects.get_or_create(
    plan_number='FAI-2026-0004',
    defaults=dict(plan_name='卫星承力框架首件检验计划', part=part4, standard='AS9102',
                  sample_size=1, description='卫星主承力框架首件检验，复合材料件。',
                  status='DRAFT', created_by=engineer1))


def make_chars(plan, rows):
    result = []
    for i, (num, name, ctype, nom, up, lo, method, crit) in enumerate(rows, 1):
        c, _ = InspectionCharacteristic.objects.get_or_create(
            plan=plan, char_number=num,
            defaults=dict(char_name=name, char_type=ctype, nominal_value=nom,
                          upper_tolerance=up, lower_tolerance=lo,
                          measurement_method=method, is_critical=crit, sequence=i))
        result.append(c)
    return result


# (num, name, type, nominal, upper_tol, lower_tol, method, critical)
CHARS1 = [
    ('DIM-001', '叶片弦长',      'DIMENSION', Decimal('85.000'), Decimal('0.100'),  Decimal('-0.100'), 'CMM',       True),
    ('DIM-002', '叶片最大厚度',  'DIMENSION', Decimal('12.500'), Decimal('0.050'),  Decimal('-0.050'), 'CMM',       True),
    ('DIM-003', '安装孔径',      'DIMENSION', Decimal('10.000'), Decimal('0.015'),  Decimal('0.000'),  'OPTICAL',   True),
    ('DIM-004', '叶根圆角半径',  'DIMENSION', Decimal('3.000'),  Decimal('0.200'),  Decimal('-0.200'), 'MECHANICAL',False),
    ('GDT-001', '叶身轮廓度',    'GD_T',      Decimal('0.000'),  Decimal('0.050'),  Decimal('-0.050'), 'LASER',     True),
    ('GDT-002', '安装面平面度',  'GD_T',      Decimal('0.000'),  Decimal('0.020'),  Decimal('-0.020'), 'CMM',       True),
    ('SUR-001', '气动面粗糙度Ra','SURFACE',   Decimal('0.800'),  Decimal('0.400'),  Decimal('-0.800'), 'MECHANICAL',False),
    ('ANG-001', '叶片安装角',    'ANGULAR',   Decimal('35.500'), Decimal('0.100'),  Decimal('-0.100'), 'CMM',       True),
]

CHARS2 = [
    ('DIM-001', '阀孔直径',     'DIMENSION', Decimal('25.000'), Decimal('0.021'),  Decimal('0.000'),  'OPTICAL',   True),
    ('DIM-002', '阀体外径',     'DIMENSION', Decimal('80.000'), Decimal('0.050'),  Decimal('-0.050'), 'MECHANICAL',False),
    ('DIM-003', '法兰厚度',     'DIMENSION', Decimal('15.000'), Decimal('0.100'),  Decimal('-0.100'), 'MECHANICAL',False),
    ('DIM-004', '密封槽宽度',   'DIMENSION', Decimal('3.200'),  Decimal('0.000'),  Decimal('-0.030'), 'MECHANICAL',True),
    ('DIM-005', '螺孔节圆直径', 'DIMENSION', Decimal('60.000'), Decimal('0.050'),  Decimal('-0.050'), 'CMM',       False),
    ('GDT-001', '螺孔位置度',   'GD_T',      Decimal('0.000'),  Decimal('0.100'),  Decimal('-0.100'), 'CMM',       True),
    ('SUR-001', '内孔粗糙度Ra', 'SURFACE',   Decimal('1.600'),  Decimal('0.400'),  Decimal('-1.600'), 'MECHANICAL',False),
]

CHARS3 = [
    ('DIM-001', '轴颈直径',     'DIMENSION', Decimal('60.000'), Decimal('-0.012'), Decimal('-0.028'), 'OPTICAL',   True),
    ('DIM-002', '轴总长',       'DIMENSION', Decimal('380.000'),Decimal('0.200'),  Decimal('-0.200'), 'MECHANICAL',False),
    ('DIM-003', '花键大径',     'DIMENSION', Decimal('72.000'), Decimal('0.025'),  Decimal('0.000'),  'MECHANICAL',True),
    ('GDT-001', '主轴颈圆柱度', 'GD_T',      Decimal('0.000'),  Decimal('0.005'),  Decimal('-0.005'), 'CMM',       True),
    ('GDT-002', '轴颈径向跳动', 'GD_T',      Decimal('0.000'),  Decimal('0.010'),  Decimal('-0.010'), 'CMM',       True),
    ('SUR-001', '轴颈粗糙度Ra', 'SURFACE',   Decimal('0.400'),  Decimal('0.400'),  Decimal('-0.400'), 'MECHANICAL',False),
]

chars1 = make_chars(plan1, CHARS1)
chars2 = make_chars(plan2, CHARS2)
chars3 = make_chars(plan3, CHARS3)

# ─────────────────────────────────────────────
# 5. 测量批次 & 测量记录
# ─────────────────────────────────────────────
print("[5/10] 创建测量批次和测量记录...")

# Batch 1 – 叶片，10样本，全部PASS
VALS1 = {
    'DIM-001': [85.030,84.975,85.020,84.985,85.010,84.995,85.025,84.970,85.015,84.980],
    'DIM-002': [12.510,12.490,12.505,12.495,12.500,12.492,12.508,12.496,12.503,12.497],
    'DIM-003': [10.006,10.008,10.010,10.007,10.009,10.005,10.011,10.008,10.006,10.010],
    'DIM-004': [3.050, 2.980, 3.020, 2.970, 3.030, 3.010, 2.990, 3.015, 2.985, 3.005],
    'GDT-001': [0.020, 0.025, 0.030, 0.018, 0.022, 0.028, 0.015, 0.032, 0.024, 0.019],
    'GDT-002': [0.008, 0.010, 0.012, 0.007, 0.009, 0.011, 0.006, 0.013, 0.008, 0.010],
    'SUR-001': [0.65,  0.72,  0.68,  0.75,  0.70,  0.66,  0.71,  0.73,  0.67,  0.69],
    'ANG-001': [35.510,35.495,35.505,35.490,35.500,35.498,35.508,35.493,35.503,35.497],
}

batch1, _ = MeasurementBatch.objects.get_or_create(
    batch_number='MB-2026-0001',
    defaults=dict(plan=plan1, sample_size=10,
                  equipment_type='CMM', equipment_id='CMM-ZEISS-001',
                  equipment_name='Zeiss Contura G3',
                  environment_temp=Decimal('20.2'), environment_humidity=Decimal('46.0'),
                  status='COMPLETED', measured_by=inspector1,
                  measured_at=timezone.now()-timedelta(days=25),
                  reviewed_by=reviewer1, reviewed_at=timezone.now()-timedelta(days=24),
                  notes='首件检验批次，10件样本全检，CMM测量室环境达标。'))

for char in chars1:
    for idx, v in enumerate(VALS1.get(char.char_number, []), 1):
        MeasurementRecord.objects.get_or_create(
            batch=batch1, characteristic=char, sample_number=idx,
            defaults={'measured_value': Decimal(str(v))})

# Batch 2 – 液压阀，5样本，DIM-004第5件FAIL → 触发NCR
VALS2 = {
    'DIM-001': [25.008,25.012,25.015,25.010,25.018],  # PASS (+0.021/0)
    'DIM-002': [79.975,80.020,79.980,80.030,80.010],  # PASS (±0.050)
    'DIM-003': [14.990,15.010,15.000,14.980,15.020],  # PASS (±0.100)
    'DIM-004': [3.195, 3.188, 3.175, 3.192, 3.162],   # 3.162 < 3.170 → FAIL
    'DIM-005': [59.980,60.020,59.990,60.010,60.000],  # PASS (±0.050)
    'GDT-001': [0.050, 0.078, 0.062, 0.071, 0.088],   # PASS (±0.100)
    'SUR-001': [1.42,  1.55,  1.48,  1.60,  1.52],    # PASS (≤2.0)
}

batch2, _ = MeasurementBatch.objects.get_or_create(
    batch_number='MB-2026-0002',
    defaults=dict(plan=plan2, sample_size=5,
                  equipment_type='CMM', equipment_id='CMM-HEX-002',
                  equipment_name='海克斯康 Global 775',
                  environment_temp=Decimal('20.5'), environment_humidity=Decimal('48.0'),
                  status='COMPLETED', measured_by=inspector1,
                  measured_at=timezone.now()-timedelta(days=5),
                  notes='液压阀体首件检验，密封槽宽度第5件超差，已开NCR。'))

for char in chars2:
    for idx, v in enumerate(VALS2.get(char.char_number, []), 1):
        MeasurementRecord.objects.get_or_create(
            batch=batch2, characteristic=char, sample_number=idx,
            defaults={'measured_value': Decimal(str(v))})

# Batch 3 – 轴，3样本，仅完成前3个特性（进行中）
VALS3 = {
    'DIM-001': [59.980,59.975,59.978],  # PASS (59.972-59.988)
    'DIM-002': [380.120,379.950,380.080],  # PASS (±0.200)
    'DIM-003': [72.015,72.010,72.018],  # PASS (+0.025/0)
}

batch3, _ = MeasurementBatch.objects.get_or_create(
    batch_number='MB-2026-0003',
    defaults=dict(plan=plan3, sample_size=3,
                  equipment_type='CMM', equipment_id='CMM-ZEISS-001',
                  equipment_name='Zeiss Contura G3',
                  environment_temp=Decimal('20.3'), environment_humidity=Decimal('45.5'),
                  status='IN_PROGRESS', measured_by=inspector1,
                  measured_at=timezone.now()-timedelta(days=2),
                  notes='测量进行中，完成尺寸类特性，形位公差待测。'))

for char in chars3:
    for idx, v in enumerate(VALS3.get(char.char_number, []), 1):
        MeasurementRecord.objects.get_or_create(
            batch=batch3, characteristic=char, sample_number=idx,
            defaults={'measured_value': Decimal(str(v))})

# ─────────────────────────────────────────────
# 6. 计算Cpk统计
# ─────────────────────────────────────────────
print("[6/10] 计算Cpk统计分析...")
batch1.calculate_all_statistics()
batch2.calculate_all_statistics()
batch3.calculate_all_statistics()

# ─────────────────────────────────────────────
# 7. 检验报告
# ─────────────────────────────────────────────
print("[7/10] 创建检验报告...")

tpl_as9102, _ = ReportTemplate.objects.get_or_create(
    name='AS9102标准模板',
    defaults=dict(standard='AS9102',
                  description='符合AS9102B标准的首件检验报告，含Form1~Form6',
                  is_active=True, created_by=admin_user))

tpl_ppap, _ = ReportTemplate.objects.get_or_create(
    name='PPAP生产件批准模板',
    defaults=dict(standard='PPAP',
                  description='PPAP Level 3提交报告模板',
                  is_active=True, created_by=admin_user))

report1, _ = InspectionReport.objects.get_or_create(
    report_number='FAI-RPT-2026-001',
    defaults=dict(plan=plan1, batch=batch1, template=tpl_as9102,
                  title='航空发动机压气机叶片首件检验报告 (AS9102)',
                  status='PUBLISHED', conclusion='PASS',
                  summary='叶片PN-2026-001 Rev.C首件检验通过。共8项特性，10件样本，全部符合图纸要求。叶身轮廓度Cpk≈1.8，过程能力良好。',
                  generated_by=admin_user, generated_at=timezone.now()-timedelta(days=23),
                  published_by=approver1, published_at=timezone.now()-timedelta(days=20)))

MaterialCertification.objects.get_or_create(
    report=report1, material_spec='TC4 Ti-6Al-4V (AMS 4928)',
    defaults=dict(cert_number='CERT-2026-TC4-0321', supplier='宝钛集团有限公司',
                  batch_number='BT-2026-A321', compliant=True,
                  notes='材料化学成分和力学性能符合AMS 4928，附材质报告。'))

SpecialProcessRecord.objects.get_or_create(
    report=report1, process_type='COATING',
    defaults=dict(spec_number='MIL-PRF-23377', processor='某航空表面处理公司',
                  cert_number='COAT-2026-0321', compliant=True,
                  notes='热障涂层厚度100-150μm，附工艺合格证。'))

report2, _ = InspectionReport.objects.get_or_create(
    report_number='FAI-RPT-2026-002',
    defaults=dict(plan=plan2, batch=batch2, template=tpl_as9102,
                  title='液压控制阀体首件检验报告 (AS9102)',
                  status='DRAFT', conclusion='',
                  summary='液压阀体PN-2026-002 Rev.B首件检验进行中。密封槽宽度（DIM-004）第5件实测3.162mm，超出下限3.170mm，NCR-2026-0001处理中。',
                  generated_by=admin_user, generated_at=timezone.now()-timedelta(days=3)))

MaterialCertification.objects.get_or_create(
    report=report2, material_spec='7075-T6 (AMS 2770)',
    defaults=dict(cert_number='CERT-2026-AL7075-0589', supplier='某铝业集团',
                  batch_number='AL-2026-B589', compliant=True))

# ─────────────────────────────────────────────
# 8. FAI项目 & 步骤
# ─────────────────────────────────────────────
print("[8/10] 创建FAI项目和步骤...")

STEP_DEFS = [
    ('PRODUCT_INFO',   '产品信息',   1),
    ('DRAWING_IMPORT', '图纸导入',   2),
    ('OCR_RECOGNITION','OCR识别',    3),
    ('DIMENSION_TABLE','尺寸公差表', 4),
    ('MEASUREMENT',    '测量数据',   5),
    ('ANALYSIS',       '统计分析',   6),
    ('REPORT',         '报告生成',   7),
    ('APPROVAL',       '审批流程',   8),
]


def make_project(number, name, desc, part, plan, batch, report, proj_status, steps_done, start_d, target_d):
    proj, _ = FAIProject.objects.get_or_create(
        project_number=number,
        defaults=dict(project_name=name, description=desc, part=part,
                      inspection_plan=plan, measurement_batch=batch, inspection_report=report,
                      status=proj_status, start_date=start_d, target_date=target_d,
                      created_by=admin_user))
    total = len(STEP_DEFS)
    for code, sname, order in STEP_DEFS:
        if steps_done == 0:
            st = 'PENDING'
        elif order <= steps_done:
            st = 'COMPLETED'
        elif order == steps_done + 1:
            st = 'IN_PROGRESS'
        else:
            st = 'PENDING'
        days_ago = (steps_done - order + 1) * 3
        ProjectStep.objects.get_or_create(
            project=proj, step_code=code,
            defaults=dict(step_name=sname, step_order=order, status=st,
                          completed_at=timezone.now()-timedelta(days=days_ago) if st == 'COMPLETED' else None,
                          completed_by=admin_user if st == 'COMPLETED' else None))
    proj.update_progress()
    return proj


today = date.today()
proj1 = make_project('PRJ-2026-0001', '压气机叶片FAI项目',
    '航空发动机压气机叶片首件检验，AS9102，全流程已完成。',
    part1, plan1, batch1, report1, 'COMPLETED', 8,
    today-timedelta(days=45), today-timedelta(days=5))

proj2 = make_project('PRJ-2026-0002', '液压阀体FAI项目',
    '飞机液压系统阀体首件检验，AS9102，密封槽NCR处理中。',
    part2, plan2, batch2, report2, 'IN_PROGRESS', 6,
    today-timedelta(days=15), today+timedelta(days=10))

proj3 = make_project('PRJ-2026-0003', '传动轴FAI项目',
    '直升机主减速器输出轴首件检验，测量进行中。',
    part3, plan3, batch3, None, 'IN_PROGRESS', 4,
    today-timedelta(days=8), today+timedelta(days=15))

proj4 = make_project('PRJ-2026-0004', '卫星框架FAI项目',
    '卫星平台主承力框架首件检验，尚未开始。',
    part4, plan4, None, None, 'DRAFT', 0,
    today, today+timedelta(days=30))

# ─────────────────────────────────────────────
# 9. 审批工作流
# ─────────────────────────────────────────────
print("[9/10] 创建审批工作流...")

# 工作流1 – 叶片检验计划审批（已完成）
wf1, _ = ApprovalWorkflow.objects.get_or_create(
    workflow_type='PLAN_APPROVAL', plan=plan1,
    defaults=dict(status='COMPLETED', current_step=3,
                  initiated_by=admin_user,
                  completed_at=timezone.now()-timedelta(days=30)))

ApprovalStep.objects.get_or_create(
    workflow=wf1, step_number=1,
    defaults=dict(step_name='SUBMIT', approver=engineer1, status='APPROVED',
                  approved_at=timezone.now()-timedelta(days=32),
                  comments='检验计划已审核，特性完整，符合AS9102要求。'))
ApprovalStep.objects.get_or_create(
    workflow=wf1, step_number=2,
    defaults=dict(step_name='REVIEW', approver=reviewer1, status='APPROVED',
                  approved_at=timezone.now()-timedelta(days=31),
                  comments='审核通过，检验方法适当。'))
ApprovalStep.objects.get_or_create(
    workflow=wf1, step_number=3,
    defaults=dict(step_name='APPROVE', approver=approver1, status='APPROVED',
                  approved_at=timezone.now()-timedelta(days=30),
                  comments='批准执行首件检验。'))

# 工作流2 – 液压阀报告审批（进行中）
wf2, _ = ApprovalWorkflow.objects.get_or_create(
    workflow_type='REPORT_APPROVAL', report=report2,
    defaults=dict(status='IN_PROGRESS', current_step=1, initiated_by=admin_user))

ApprovalStep.objects.get_or_create(
    workflow=wf2, step_number=1,
    defaults=dict(step_name='REVIEW', approver=reviewer1, status='PENDING'))
ApprovalStep.objects.get_or_create(
    workflow=wf2, step_number=2,
    defaults=dict(step_name='APPROVE', approver=approver1, status='PENDING'))

# ─────────────────────────────────────────────
# 10. NCR不合格品报告
# ─────────────────────────────────────────────
print("[10/10] 创建NCR不合格品报告...")

char_seal = InspectionCharacteristic.objects.get(plan=plan2, char_number='DIM-004')
failed_rec = MeasurementRecord.objects.filter(
    batch=batch2, characteristic=char_seal, status='FAIL').first()

ncr1, _ = NonConformanceReport.objects.get_or_create(
    ncr_number='NCR-2026-0001',
    defaults=dict(
        part=part2,
        measurement_record=failed_rec,
        product_name='液压系统控制阀体',
        specification='PN-2026-002 Rev.B',
        batch_number='MB-2026-0002',
        department_code='QD-002',
        problem_type='DIMENSION',
        problem_description='密封槽宽度（DIM-004）第5件实测3.162mm，图纸要求3.17-3.20mm，超出下限0.008mm。',
        defect_phenomenon='密封槽宽度超差，实测3.162mm < 下限3.170mm',
        supply_method='INTERNAL',
        status='IN_PROGRESS',
        responsible_person=engineer1,
        inspector=inspector1,
        inspected_at=timezone.now()-timedelta(days=5),
        notes='判断为铣削工序刀具磨损导致，需更换刀具并调整工艺参数后重新加工。'))

NonConformanceAction.objects.get_or_create(
    ncr=ncr1, action_type='REWORK',
    defaults=dict(
        action_description='对第5件阀体密封槽重新铣削，调整进给量和刀具补偿值，确保宽度3.17-3.20mm。',
        responsible_person=engineer1,
        due_date=today+timedelta(days=3),
        status='IN_PROGRESS'))

# ─────────────────────────────────────────────
# 汇总输出
# ─────────────────────────────────────────────
from measurements.models import StatisticalAnalysis

print("\n" + "=" * 60)
print("演示数据生成完成！")
print("=" * 60)
print("""
账号列表（密码见括号）:
  admin       (admin123)  系统管理员
  inspector1  (demo123)   质量检验员 - 王明
  reviewer1   (demo123)   质量审核员 - 李华
  approver1   (demo123)   质量经理   - 张总
  engineer1   (demo123)   质量工程师 - 刘工
""")
print(f"  零件:     {Part.objects.count()} 个")
print(f"  FAI项目:  {FAIProject.objects.count()} 个")
print(f"  SOP文档:  {SOPDocument.objects.count()} 个")
print(f"  检验计划: {InspectionPlan.objects.count()} 个")
print(f"  检验特性: {InspectionCharacteristic.objects.count()} 个")
print(f"  测量批次: {MeasurementBatch.objects.count()} 个")
print(f"  测量记录: {MeasurementRecord.objects.count()} 条")
print(f"  统计分析: {StatisticalAnalysis.objects.count()} 条")
print(f"  检验报告: {InspectionReport.objects.count()} 个")
print(f"  审批流程: {ApprovalWorkflow.objects.count()} 个")
print(f"  NCR报告:  {NonConformanceReport.objects.count()} 个")

print("\nCpk统计摘要（批次1 - 压气机叶片）:")
for sa in StatisticalAnalysis.objects.filter(batch=batch1).select_related('characteristic').order_by('characteristic__sequence'):
    cpk_str = f"{float(sa.cpk):.3f} ({sa.process_capability})" if sa.cpk is not None else "N/A"
    print(f"  [{sa.characteristic.char_number}] {sa.characteristic.char_name[:12]:12s}: Cpk={cpk_str}")

print("\nCpk统计摘要（批次2 - 液压阀体，含NCR特性）:")
for sa in StatisticalAnalysis.objects.filter(batch=batch2).select_related('characteristic').order_by('characteristic__sequence'):
    cpk_str = f"{float(sa.cpk):.3f} ({sa.process_capability})" if sa.cpk is not None else "N/A"
    flag = " ← NCR" if sa.characteristic.char_number == 'DIM-004' else ""
    print(f"  [{sa.characteristic.char_number}] {sa.characteristic.char_name[:12]:12s}: Cpk={cpk_str}{flag}")

print(f"\n请访问 http://localhost:5000 查看演示数据！")
