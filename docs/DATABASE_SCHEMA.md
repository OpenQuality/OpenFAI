# FAI系统数据库设计文档

> 版本: 1.0.0  
> 更新日期: 2026年3月

---

## 1. 数据库概述

### 1.1 数据库类型

- **生产环境**: PostgreSQL 14+
- **开发环境**: SQLite 3

### 1.2 数据库命名规范

- 表名: 小写字母，使用下划线分隔，如 `inspection_plans`
- 字段名: 小写字母，使用下划线分隔
- 主键: UUID类型，命名为 `id`
- 外键: 关联表名单数形式加 `_id`，如 `part_id`

---

## 2. 核心数据模型

### 2.1 用户与权限 (accounts)

#### auth_user (Django内置用户表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK | 主键 |
| username | VARCHAR(150) | UNIQUE, NOT NULL | 用户名 |
| password | VARCHAR(128) | NOT NULL | 密码哈希 |
| email | VARCHAR(254) | | 邮箱 |
| first_name | VARCHAR(150) | | 名 |
| last_name | VARCHAR(150) | | 姓 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| is_staff | BOOLEAN | DEFAULT FALSE | 是否员工 |
| is_superuser | BOOLEAN | DEFAULT FALSE | 是否超级用户 |
| date_joined | DATETIME | | 注册时间 |
| last_login | DATETIME | | 最后登录时间 |

#### UserProfile (用户扩展信息)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| user | FK(auth_user) | UNIQUE | 关联用户 |
| department | VARCHAR(100) | | 部门 |
| position | VARCHAR(100) | | 职位 |
| phone | VARCHAR(20) | | 电话 |
| avatar | VARCHAR(200) | | 头像URL |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

---

### 2.2 零件管理 (parts)

#### parts (零件表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| part_number | VARCHAR(100) | UNIQUE, NOT NULL | 零件编号 |
| part_name | VARCHAR(200) | NOT NULL | 零件名称 |
| revision | VARCHAR(20) | NOT NULL, DEFAULT 'A' | 版本号 |
| description | TEXT | | 描述 |
| cad_file | VARCHAR(500) | NULL | CAD文件路径 |
| cad_file_type | VARCHAR(20) | DEFAULT '' | CAD文件类型 |
| drawing_file | VARCHAR(500) | NULL | 图纸文件路径 |
| material | VARCHAR(100) | DEFAULT '' | 材料 |
| weight | DECIMAL(10,3) | NULL | 重量(kg) |
| surface_treatment | VARCHAR(200) | DEFAULT '' | 表面处理 |
| customer | VARCHAR(200) | DEFAULT '' | 客户 |
| customer_part_number | VARCHAR(100) | DEFAULT '' | 客户零件编号 |
| batch_serial_number | VARCHAR(100) | NULL | 批次/序列号 |
| order_number | VARCHAR(100) | NULL | 订单号 |
| production_quantity | INTEGER | DEFAULT 0 | 生产数量 |
| fai_quantity | INTEGER | DEFAULT 1 | 首件数量 |
| department | VARCHAR(100) | NULL | 单位/部门 |
| operator | VARCHAR(100) | NULL | 操作者 |
| status | VARCHAR(20) | DEFAULT 'DRAFT' | 状态 |
| created_by | FK(auth_user) | NULL | 创建人 |
| updated_by | FK(auth_user) | NULL | 更新人 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**状态枚举 (status)**:
- DRAFT: 草稿
- PENDING: 待审核
- ACTIVE: 激活
- INACTIVE: 停用

#### cad_extractions (CAD解析记录表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| part | FK(parts) | NOT NULL | 关联零件 |
| extraction_data | JSONB | NULL | 解析数据(JSON) |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| extracted_at | DATETIME | NULL | 解析时间 |
| error_message | TEXT | NULL | 错误信息 |
| created_at | DATETIME | | 创建时间 |

**状态枚举 (status)**:
- PENDING: 待处理
- PROCESSING: 处理中
- COMPLETED: 已完成
- FAILED: 失败

#### dimensions (尺寸表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| extraction | FK(cad_extractions) | NOT NULL | 关联解析记录 |
| dim_id | VARCHAR(50) | NOT NULL | 尺寸ID |
| dim_type | VARCHAR(30) | NOT NULL | 尺寸类型 |
| name | VARCHAR(100) | NOT NULL | 尺寸名称 |
| nominal_value | DECIMAL(15,6) | NOT NULL | 公称值 |
| upper_tolerance | DECIMAL(10,6) | DEFAULT 0 | 上偏差 |
| lower_tolerance | DECIMAL(10,6) | DEFAULT 0 | 下偏差 |
| unit | VARCHAR(10) | DEFAULT 'mm' | 单位 |
| is_critical | BOOLEAN | DEFAULT FALSE | 是否关键特性 |

**尺寸类型枚举 (dim_type)**:
- LINEAR: 线性尺寸
- DIAMETER: 直径
- RADIUS: 半径
- ANGLE: 角度
- GD_T: 形位公差

---

### 2.3 检验计划 (inspections)

#### inspection_plans (检验计划表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| plan_number | VARCHAR(50) | UNIQUE | 计划编号 |
| plan_name | VARCHAR(200) | NOT NULL | 计划名称 |
| part | FK(parts) | NOT NULL | 关联零件 |
| standard | VARCHAR(20) | DEFAULT 'AS9102' | 标准 |
| sample_size | INTEGER | DEFAULT 1 | 样本数量 |
| description | TEXT | | 描述 |
| status | VARCHAR(20) | DEFAULT 'DRAFT' | 状态 |
| approved_by | FK(auth_user) | NULL | 批准人 |
| approved_at | DATETIME | NULL | 批准时间 |
| created_by | FK(auth_user) | NULL | 创建人 |
| updated_by | FK(auth_user) | NULL | 更新人 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**标准枚举 (standard)**:
- AS9102: 航空航天标准
- PPAP: 生产件批准程序
- CUSTOM: 自定义

**状态枚举 (status)**:
- DRAFT: 草稿
- PENDING_REVIEW: 待审核
- ACTIVE: 激活
- COMPLETED: 已完成
- ARCHIVED: 已归档

#### characteristic_categories (特性分类表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(100) | NOT NULL | 分类名称 |
| code | VARCHAR(50) | UNIQUE | 分类代码 |
| description | TEXT | | 描述 |
| created_at | DATETIME | | 创建时间 |

#### inspection_characteristics (检验特性表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| plan | FK(inspection_plans) | NOT NULL | 关联计划 |
| category | FK(characteristic_categories) | NULL | 分类 |
| char_number | VARCHAR(50) | NOT NULL | 特性编号 |
| char_name | VARCHAR(200) | NOT NULL | 特性名称 |
| char_type | VARCHAR(30) | DEFAULT 'DIMENSION' | 特性类型 |
| nominal_value | DECIMAL(15,6) | NOT NULL | 公称值 |
| upper_tolerance | DECIMAL(10,6) | DEFAULT 0 | 上偏差 |
| lower_tolerance | DECIMAL(10,6) | DEFAULT 0 | 下偏差 |
| unit | VARCHAR(10) | DEFAULT 'mm' | 单位 |
| is_critical | BOOLEAN | DEFAULT FALSE | 是否关键特性 |
| is_key_characteristic | BOOLEAN | DEFAULT FALSE | 是否关键特性(KC) |
| inspection_method | VARCHAR(100) | DEFAULT '' | 检验方法 |
| gage | VARCHAR(100) | DEFAULT '' | 量具 |
| sequence | INTEGER | DEFAULT 0 | 顺序 |
| created_at | DATETIME | | 创建时间 |

**特性类型枚举 (char_type)**:
- DIMENSION: 尺寸
- GD_T: 形位公差
- SURFACE: 表面特性
- MATERIAL: 材料特性
- OTHER: 其他

---

### 2.4 测量数据 (measurements)

#### measurement_batches (测量批次表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| batch_number | VARCHAR(50) | UNIQUE | 批次号 |
| plan | FK(inspection_plans) | NOT NULL | 关联计划 |
| equipment_type | VARCHAR(50) | NULL | 设备类型 |
| equipment_id | VARCHAR(100) | NULL | 设备编号 |
| environment_temp | DECIMAL(5,2) | NULL | 环境温度 |
| environment_humidity | DECIMAL(5,2) | NULL | 环境湿度 |
| measured_at | DATETIME | NULL | 测量时间 |
| measured_by | FK(auth_user) | NULL | 测量人 |
| status | VARCHAR(20) | DEFAULT 'DRAFT' | 状态 |
| notes | TEXT | | 备注 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**状态枚举 (status)**:
- DRAFT: 草稿
- IN_PROGRESS: 进行中
- COMPLETED: 已完成

#### measurement_records (测量记录表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| batch | FK(measurement_batches) | NOT NULL | 关联批次 |
| characteristic | FK(inspection_characteristics) | NOT NULL | 关联特性 |
| sample_number | INTEGER | DEFAULT 1 | 样本号 |
| measured_value | DECIMAL(15,6) | NOT NULL | 测量值 |
| deviation | DECIMAL(15,6) | NULL | 偏差 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| notes | TEXT | | 备注 |
| created_at | DATETIME | | 创建时间 |

**状态枚举 (status)**:
- PASS: 合格
- FAIL: 不合格
- PENDING: 待判定

#### statistical_analyses (统计分析表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| characteristic | FK(inspection_characteristics) | NOT NULL | 关联特性 |
| batch | FK(measurement_batches) | NOT NULL | 关联批次 |
| sample_count | INTEGER | | 样本数量 |
| mean | DECIMAL(15,6) | | 均值 |
| std_dev | DECIMAL(15,6) | | 标准差 |
| min_value | DECIMAL(15,6) | | 最小值 |
| max_value | DECIMAL(15,6) | | 最大值 |
| range_value | DECIMAL(15,6) | | 极差 |
| cp | DECIMAL(10,4) | | 过程能力指数Cp |
| cpk | DECIMAL(10,4) | | 过程能力指数Cpk |
| created_at | DATETIME | | 创建时间 |

---

### 2.5 检验报告 (reports)

#### report_templates (报告模板表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 模板名称 |
| standard | VARCHAR(20) | DEFAULT 'AS9102' | 适用标准 |
| template_file | VARCHAR(500) | NULL | 模板文件 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否启用 |
| created_at | DATETIME | | 创建时间 |

#### inspection_reports (检验报告表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| report_number | VARCHAR(50) | UNIQUE | 报告编号 |
| title | VARCHAR(200) | NOT NULL | 报告标题 |
| plan | FK(inspection_plans) | NOT NULL | 关联计划 |
| batch | FK(measurement_batches) | NOT NULL | 关联批次 |
| template | FK(report_templates) | NULL | 模板 |
| standard | VARCHAR(20) | DEFAULT 'AS9102' | 标准 |
| summary | TEXT | | 摘要 |
| conclusion | VARCHAR(20) | NULL | 结论 |
| status | VARCHAR(20) | DEFAULT 'DRAFT' | 状态 |
| generated_at | DATETIME | NULL | 生成时间 |
| generated_by | FK(auth_user) | NULL | 生成人 |
| published_at | DATETIME | NULL | 发布时间 |
| published_by | FK(auth_user) | NULL | 发布人 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**结论枚举 (conclusion)**:
- PASS: 合格
- FAIL: 不合格
- PENDING: 待判定

**状态枚举 (status)**:
- DRAFT: 草稿
- GENERATING: 生成中
- COMPLETED: 已完成
- PUBLISHED: 已发布

---

### 2.6 工作流管理 (workflows)

#### approval_workflows (审批工作流表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| workflow_type | VARCHAR(50) | NOT NULL | 工作流类型 |
| plan | FK(inspection_plans) | NULL | 关联计划 |
| report | FK(inspection_reports) | NULL | 关联报告 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| current_step | INTEGER | DEFAULT 1 | 当前步骤 |
| initiated_by | FK(auth_user) | NULL | 发起人 |
| initiated_at | DATETIME | | 发起时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| notes | TEXT | | 备注 |

**工作流类型枚举 (workflow_type)**:
- PLAN_APPROVAL: 检验计划审批
- REPORT_APPROVAL: 检验报告审批

**状态枚举 (status)**:
- PENDING: 待处理
- IN_PROGRESS: 进行中
- COMPLETED: 已完成
- REJECTED: 已拒绝
- CANCELLED: 已取消

#### approval_steps (审批步骤表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| workflow | FK(approval_workflows) | NOT NULL | 关联工作流 |
| step_number | INTEGER | NOT NULL | 步骤号 |
| step_name | VARCHAR(100) | NOT NULL | 步骤名称 |
| approver | FK(auth_user) | NULL | 审批人 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| approved_at | DATETIME | NULL | 审批时间 |
| comments | TEXT | | 审批意见 |
| created_at | DATETIME | | 创建时间 |

**步骤名称枚举 (step_name)**:
- SUBMIT: 提交
- REVIEW: 审核
- APPROVE: 批准

**状态枚举 (status)**:
- PENDING: 待处理
- APPROVED: 已通过
- REJECTED: 已拒绝
- SKIPPED: 已跳过

#### electronic_signatures (电子签名表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| step | FK(approval_steps) | NOT NULL | 关联步骤 |
| user | FK(auth_user) | NOT NULL | 签名人 |
| signature_image | VARCHAR(500) | NULL | 签名图片 |
| signed_at | DATETIME | | 签名时间 |
| ip_address | VARCHAR(45) | NULL | IP地址 |
| user_agent | VARCHAR(255) | NULL | 用户代理 |

#### non_conformance_reports (不合格品报告表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| ncr_number | VARCHAR(50) | UNIQUE | NCR编号 |
| measurement_record | FK(measurement_records) | NULL | 关联测量记录 |
| product_name | VARCHAR(200) | NOT NULL | 品名 |
| specification | VARCHAR(200) | DEFAULT '' | 规格 |
| batch_number | VARCHAR(100) | DEFAULT '' | 批次号 |
| department_code | VARCHAR(50) | DEFAULT '' | 科号 |
| problem_type | VARCHAR(20) | NOT NULL | 问题类型 |
| problem_description | TEXT | NOT NULL | 问题描述 |
| defect_phenomenon | VARCHAR(500) | DEFAULT '' | 不良现象 |
| supply_method | VARCHAR(20) | DEFAULT 'INTERNAL' | 供应方式 |
| supplier_name | VARCHAR(200) | DEFAULT '' | 供方名称 |
| delivery_date | DATE | NULL | 交货日期 |
| status | VARCHAR(20) | DEFAULT 'OPEN' | 状态 |
| responsible_person | FK(auth_user) | NULL | 负责人 |
| inspector | FK(auth_user) | NULL | 检验人 |
| inspected_at | DATETIME | NULL | 检验时间 |
| attachment | VARCHAR(500) | NULL | 附件 |
| notes | TEXT | | 备注 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**问题类型枚举 (problem_type)**:
- DIMENSION: 尺寸超差
- APPEARANCE: 外观缺陷
- MATERIAL: 材料问题
- PROCESS: 工艺问题
- ASSEMBLY: 装配问题
- OTHER: 其他

**供应方式枚举 (supply_method)**:
- INTERNAL: 内部加工
- EXTERNAL: 外协加工
- PURCHASED: 外购件

**状态枚举 (status)**:
- OPEN: 待处理
- IN_PROGRESS: 处理中
- PENDING_REVIEW: 待审核
- CLOSED: 已关闭
- CANCELLED: 已取消

#### non_conformance_actions (不合格品处理措施表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| ncr | FK(non_conformance_reports) | NOT NULL | 关联NCR |
| action_type | VARCHAR(30) | NOT NULL | 措施类型 |
| action_description | TEXT | NOT NULL | 措施描述 |
| responsible_person | FK(auth_user) | NULL | 责任人 |
| due_date | DATE | NULL | 计划日期 |
| completed_at | DATE | NULL | 完成日期 |
| completion_notes | TEXT | | 完成说明 |
| verified_by | FK(auth_user) | NULL | 验证人 |
| verified_at | DATETIME | NULL | 验证时间 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| created_at | DATETIME | | 创建时间 |

**措施类型枚举 (action_type)**:
- REWORK: 返工
- REPAIR: 返修
- SCRAP: 报废
- CONCESSION: 让步接收
- RETURN: 退货
- REVIEW: 评审
- CORRECTIVE: 纠正措施

**状态枚举 (status)**:
- PENDING: 待执行
- IN_PROGRESS: 进行中
- COMPLETED: 已完成
- VERIFIED: 已验证

---

### 2.7 项目管理 (core)

#### fai_projects (FAI项目表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| project_number | VARCHAR(100) | UNIQUE | 项目编号 |
| project_name | VARCHAR(200) | NOT NULL | 项目名称 |
| description | TEXT | | 描述 |
| status | VARCHAR(20) | DEFAULT 'DRAFT' | 状态 |
| progress_percentage | INTEGER | DEFAULT 0 | 完成进度 |
| start_date | DATE | NULL | 开始日期 |
| target_date | DATE | NULL | 目标日期 |
| completed_date | DATE | NULL | 完成日期 |
| created_by | FK(auth_user) | NULL | 创建人 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

**状态枚举 (status)**:
- DRAFT: 草稿
- IN_PROGRESS: 进行中
- PENDING_REVIEW: 待审核
- COMPLETED: 已完成
- ARCHIVED: 已归档

#### project_steps (项目步骤表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| project | FK(fai_projects) | NOT NULL | 关联项目 |
| step_code | VARCHAR(30) | NOT NULL | 步骤代码 |
| step_name | VARCHAR(100) | NOT NULL | 步骤名称 |
| step_order | INTEGER | DEFAULT 1 | 步骤顺序 |
| status | VARCHAR(20) | DEFAULT 'PENDING' | 状态 |
| completed_at | DATETIME | NULL | 完成时间 |
| completed_by | FK(auth_user) | NULL | 完成人 |
| notes | TEXT | | 备注 |
| created_at | DATETIME | | 创建时间 |

**步骤代码枚举 (step_code)**:
- PRODUCT_INFO: 产品信息
- DRAWING_IMPORT: 图纸导入
- OCR_RECOGNITION: OCR识别
- DIMENSION_TABLE: 尺寸公差表
- MEASUREMENT: 测量数据
- ANALYSIS: 统计分析
- REPORT: 报告生成
- APPROVAL: 审批流程

**状态枚举 (status)**:
- PENDING: 待处理
- IN_PROGRESS: 进行中
- COMPLETED: 已完成
- SKIPPED: 已跳过

---

### 2.8 设备管理 (equipment)

#### equipment (设备表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| equipment_id | VARCHAR(100) | UNIQUE | 设备编号 |
| name | VARCHAR(200) | NOT NULL | 设备名称 |
| equipment_type | VARCHAR(50) | NOT NULL | 设备类型 |
| manufacturer | VARCHAR(200) | | 制造商 |
| model | VARCHAR(100) | | 型号 |
| serial_number | VARCHAR(100) | | 序列号 |
| calibration_date | DATE | NULL | 校准日期 |
| next_calibration_date | DATE | NULL | 下次校准日期 |
| status | VARCHAR(20) | DEFAULT 'ACTIVE' | 状态 |
| location | VARCHAR(200) | | 位置 |
| notes | TEXT | | 备注 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

---

### 2.9 系统日志 (core)

#### system_logs (系统日志表)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PK | 主键 |
| user | FK(auth_user) | NULL | 操作用户 |
| action | VARCHAR(20) | NOT NULL | 操作类型 |
| model_name | VARCHAR(100) | NOT NULL | 模型名称 |
| object_id | VARCHAR(100) | | 对象ID |
| description | TEXT | NOT NULL | 操作描述 |
| ip_address | VARCHAR(45) | NULL | IP地址 |
| user_agent | VARCHAR(255) | | 用户代理 |
| created_at | DATETIME | | 操作时间 |

---

## 3. 索引设计

### 3.1 主要索引

```sql
-- 零件表索引
CREATE INDEX idx_parts_part_number ON parts(part_number);
CREATE INDEX idx_parts_status ON parts(status);
CREATE INDEX idx_parts_created_by ON parts(created_by);

-- 检验计划表索引
CREATE INDEX idx_plans_part ON inspection_plans(part_id);
CREATE INDEX idx_plans_status ON inspection_plans(status);

-- 测量记录表索引
CREATE INDEX idx_records_batch ON measurement_records(batch_id);
CREATE INDEX idx_records_characteristic ON measurement_records(characteristic_id);
CREATE INDEX idx_records_status ON measurement_records(status);

-- 审批工作流表索引
CREATE INDEX idx_workflows_status ON approval_workflows(status);
CREATE INDEX idx_workflows_initiated_by ON approval_workflows(initiated_by);

-- 不合格品报告表索引
CREATE INDEX idx_ncr_status ON non_conformance_reports(status);
CREATE INDEX idx_ncr_inspector ON non_conformance_reports(inspector);
```

---

## 4. 数据库迁移策略

### 4.1 迁移原则

1. **向后兼容**: 新迁移不应破坏现有数据
2. **分步执行**: 复杂变更拆分为多个迁移
3. **数据安全**: 添加NOT NULL前先处理NULL值
4. **可回滚**: 每个迁移都应提供回滚方案

### 4.2 迁移文件清单

```
parts/migrations/
├── 0001_initial.py                        # 初始化零件表
├── 0002_part_batch_serial_number_*.py     # 添加产品信息字段
└── 0003_fix_fai_quantity_defaults.py      # 修复字段约束

core/migrations/
├── 0001_initial.py                        # 初始化核心表
└── 0002_faiproject_projectstep.py         # 添加项目管理表

workflows/migrations/
├── 0001_initial.py                        # 初始化工作流表
└── 0002_nonconformancereport_*.py         # 添加不合格品处理表
```

### 4.3 生产环境迁移注意事项

```sql
-- 1. 添加可空字段
ALTER TABLE parts ADD COLUMN new_field VARCHAR(100) NULL;

-- 2. 更新现有数据
UPDATE parts SET new_field = 'default_value' WHERE new_field IS NULL;

-- 3. 添加约束
ALTER TABLE parts ALTER COLUMN new_field SET NOT NULL;
ALTER TABLE parts ALTER COLUMN new_field SET DEFAULT 'default_value';
```

---

## 5. 数据完整性约束

### 5.1 外键约束

```sql
-- 级联删除示例
ALTER TABLE inspection_characteristics 
ADD CONSTRAINT fk_characteristic_plan 
FOREIGN KEY (plan_id) REFERENCES inspection_plans(id) 
ON DELETE CASCADE;

-- 级联更新示例
ALTER TABLE measurement_records 
ADD CONSTRAINT fk_record_batch 
FOREIGN KEY (batch_id) REFERENCES measurement_batches(id) 
ON UPDATE CASCADE ON DELETE CASCADE;
```

### 5.2 检查约束

```sql
-- 数值范围约束
ALTER TABLE inspection_characteristics 
ADD CONSTRAINT chk_tolerance 
CHECK (upper_tolerance >= 0 AND lower_tolerance <= 0);

-- 进度范围约束
ALTER TABLE fai_projects 
ADD CONSTRAINT chk_progress 
CHECK (progress_percentage >= 0 AND progress_percentage <= 100);
```

---

## 6. 数据库视图

### 6.1 常用视图

```sql
-- 检验计划概览视图
CREATE VIEW v_plan_overview AS
SELECT 
    p.id,
    p.plan_number,
    p.plan_name,
    p.status,
    part.part_number,
    part.part_name,
    COUNT(c.id) as characteristic_count
FROM inspection_plans p
LEFT JOIN parts part ON p.part_id = part.id
LEFT JOIN inspection_characteristics c ON c.plan_id = p.id
GROUP BY p.id, p.plan_number, p.plan_name, p.status, 
         part.part_number, part.part_name;

-- 测量结果统计视图
CREATE VIEW v_measurement_stats AS
SELECT 
    b.id as batch_id,
    b.batch_number,
    COUNT(r.id) as total_count,
    SUM(CASE WHEN r.status = 'PASS' THEN 1 ELSE 0 END) as pass_count,
    SUM(CASE WHEN r.status = 'FAIL' THEN 1 ELSE 0 END) as fail_count
FROM measurement_batches b
LEFT JOIN measurement_records r ON r.batch_id = b.id
GROUP BY b.id, b.batch_number;
```

---

**文档版本历史**

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-03-13 | 初始版本 | FAI开发团队 |
