# FAI系统 API 接口文档

> 版本: 1.0.0  
> 更新日期: 2026年3月  
> 基础路径: `/api/v1`

---

## 目录

1. [接口概述](#1-接口概述)
2. [认证方式](#2-认证方式)
3. [通用规范](#3-通用规范)
4. [零件管理API](#4-零件管理api)
5. [检验计划API](#5-检验计划api)
6. [测量数据API](#6-测量数据api)
7. [检验报告API](#7-检验报告api)
8. [工作流管理API](#8-工作流管理api)
9. [项目管理API](#9-项目管理api)
10. [设备管理API](#10-设备管理api)
11. [错误码参考](#11-错误码参考)

---

## 1. 接口概述

### 1.1 API基础信息

| 项目 | 说明 |
|------|------|
| 协议 | HTTP/HTTPS |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| API版本 | v1 |
| 基础路径 | /api/v1 |

### 1.2 请求方法说明

| 方法 | 说明 | 幂等性 |
|------|------|--------|
| GET | 获取资源 | 是 |
| POST | 创建资源 | 否 |
| PUT | 完整更新资源 | 是 |
| PATCH | 部分更新资源 | 否 |
| DELETE | 删除资源 | 是 |

---

## 2. 认证方式

### 2.1 Session认证 (Web应用)

```http
Cookie: sessionid=<session_key>
```

适用于浏览器前端应用，通过登录接口获取session。

### 2.2 Token认证 (API调用)

```http
Authorization: Token <token_value>
```

适用于API客户端调用，需要在请求头中携带Token。

### 2.3 登录接口

```http
POST /api/v1/auth/login/

请求体:
{
    "username": "admin",
    "password": "password123"
}

响应:
{
    "success": true,
    "message": "登录成功",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com"
    }
}
```

### 2.4 登出接口

```http
POST /api/v1/auth/logout/

响应:
{
    "success": true,
    "message": "登出成功"
}
```

---

## 3. 通用规范

### 3.1 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量(最大100) |

### 3.2 分页响应格式

```json
{
    "count": 100,
    "next": "http://api.example.com/api/v1/parts/?page=2",
    "previous": null,
    "results": [
        // 数据列表
    ]
}
```

### 3.3 过滤参数

| 参数 | 类型 | 说明 |
|------|------|------|
| search | string | 关键词搜索 |
| ordering | string | 排序字段(前缀-表示降序) |
| status | string | 状态过滤 |

### 3.4 错误响应格式

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "参数验证失败",
        "details": {
            "field": "part_number",
            "message": "该字段不能为空"
        }
    }
}
```

---

## 4. 零件管理API

### 4.1 获取零件列表

```http
GET /api/v1/parts/api/

参数:
- search: 搜索关键词(零件编号、名称)
- status: 状态过滤
- ordering: 排序字段

响应:
{
    "count": 50,
    "next": "?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "part_number": "P001",
            "part_name": "零件A",
            "revision": "A",
            "description": "零件描述",
            "material": "铝合金",
            "status": "ACTIVE",
            "created_at": "2026-03-01T10:00:00Z",
            "updated_at": "2026-03-01T10:00:00Z"
        }
    ]
}
```

### 4.2 创建零件

```http
POST /api/v1/parts/api/

请求体:
{
    "part_number": "P002",
    "part_name": "新零件",
    "revision": "A",
    "description": "零件描述",
    "material": "钢",
    "weight": 1.5,
    "surface_treatment": "镀锌",
    "customer": "客户A",
    "customer_part_number": "CP001",
    "batch_serial_number": "B2026001",
    "order_number": "O2026001",
    "production_quantity": 100,
    "fai_quantity": 5,
    "department": "生产部",
    "operator": "张三"
}

响应 (201 Created):
{
    "id": "uuid",
    "part_number": "P002",
    "part_name": "新零件",
    "revision": "A",
    "status": "DRAFT",
    "created_at": "2026-03-01T10:00:00Z"
}
```

### 4.3 获取零件详情

```http
GET /api/v1/parts/api/{id}/

响应:
{
    "id": "uuid",
    "part_number": "P001",
    "part_name": "零件A",
    "revision": "A",
    "description": "零件描述",
    "cad_file": "https://storage.example.com/cad/file.step",
    "cad_file_type": "STEP",
    "drawing_file": "https://storage.example.com/drawing/file.pdf",
    "material": "铝合金",
    "weight": 1.5,
    "surface_treatment": "阳极氧化",
    "customer": "客户A",
    "customer_part_number": "CP001",
    "batch_serial_number": "B2026001",
    "order_number": "O2026001",
    "production_quantity": 100,
    "fai_quantity": 5,
    "department": "生产部",
    "operator": "张三",
    "status": "ACTIVE",
    "created_by": {
        "id": 1,
        "username": "admin"
    },
    "updated_by": {
        "id": 1,
        "username": "admin"
    },
    "created_at": "2026-03-01T10:00:00Z",
    "updated_at": "2026-03-01T10:00:00Z",
    "cad_extraction": {
        "id": "uuid",
        "status": "COMPLETED",
        "dimension_count": 50
    },
    "inspection_plans": [
        {
            "id": "uuid",
            "plan_number": "IP001",
            "plan_name": "检验计划1",
            "status": "ACTIVE"
        }
    ]
}
```

### 4.4 更新零件

```http
PUT /api/v1/parts/api/{id}/

请求体:
{
    "part_name": "更新后的零件名称",
    "description": "更新后的描述",
    "weight": 2.0
}

响应 (200 OK):
{
    "id": "uuid",
    "part_name": "更新后的零件名称",
    "updated_at": "2026-03-01T12:00:00Z"
}
```

### 4.5 删除零件

```http
DELETE /api/v1/parts/api/{id}/

响应 (204 No Content)
```

### 4.6 上传CAD文件

```http
POST /api/v1/parts/api/{id}/upload_cad/

请求体 (multipart/form-data):
- cad_file: CAD文件 (支持 .step, .stp, .iges, .igs, .dxf 格式)

响应:
{
    "success": true,
    "message": "CAD文件上传成功",
    "file_url": "https://storage.example.com/cad/file.step",
    "file_type": "STEP"
}
```

### 4.7 解析CAD文件

```http
POST /api/v1/parts/api/{id}/parse_cad/

响应:
{
    "success": true,
    "message": "CAD解析任务已启动",
    "extraction_id": "uuid"
}
```

### 4.8 获取CAD解析结果

```http
GET /api/v1/parts/api/{id}/cad_extraction/

响应:
{
    "id": "uuid",
    "status": "COMPLETED",
    "extracted_at": "2026-03-01T10:30:00Z",
    "dimensions": [
        {
            "id": "uuid",
            "dim_id": "D1",
            "dim_type": "LINEAR",
            "name": "长度",
            "nominal_value": 100.0,
            "upper_tolerance": 0.1,
            "lower_tolerance": -0.1,
            "unit": "mm",
            "is_critical": false
        }
    ],
    "dimension_count": 50,
    "critical_count": 5
}
```

---

## 5. 检验计划API

### 5.1 获取检验计划列表

```http
GET /api/v1/inspections/plans/

参数:
- part: 零件ID
- status: 状态过滤
- search: 搜索关键词

响应:
{
    "count": 20,
    "results": [
        {
            "id": "uuid",
            "plan_number": "IP001",
            "plan_name": "检验计划1",
            "part": {
                "id": "uuid",
                "part_number": "P001",
                "part_name": "零件A"
            },
            "standard": "AS9102",
            "sample_size": 5,
            "status": "ACTIVE",
            "characteristic_count": 50,
            "created_at": "2026-03-01T10:00:00Z"
        }
    ]
}
```

### 5.2 创建检验计划

```http
POST /api/v1/inspections/plans/

请求体:
{
    "plan_name": "新检验计划",
    "part": "part_uuid",
    "standard": "AS9102",
    "sample_size": 5,
    "description": "计划描述"
}

响应 (201 Created):
{
    "id": "uuid",
    "plan_number": "IP002",
    "plan_name": "新检验计划",
    "status": "DRAFT"
}
```

### 5.3 获取检验计划详情

```http
GET /api/v1/inspections/plans/{id}/

响应:
{
    "id": "uuid",
    "plan_number": "IP001",
    "plan_name": "检验计划1",
    "part": {
        "id": "uuid",
        "part_number": "P001",
        "part_name": "零件A"
    },
    "standard": "AS9102",
    "sample_size": 5,
    "status": "ACTIVE",
    "characteristics": [
        {
            "id": "uuid",
            "char_number": "C1",
            "char_name": "外径",
            "char_type": "DIMENSION",
            "nominal_value": 50.0,
            "upper_tolerance": 0.05,
            "lower_tolerance": -0.05,
            "unit": "mm",
            "is_critical": true,
            "inspection_method": "千分尺",
            "gage": "千分尺0-75"
        }
    ],
    "characteristic_count": 50,
    "critical_count": 5
}
```

### 5.4 添加检验特性

```http
POST /api/v1/inspections/plans/{id}/add_characteristic/

请求体:
{
    "char_number": "C51",
    "char_name": "新特性",
    "char_type": "DIMENSION",
    "nominal_value": 25.0,
    "upper_tolerance": 0.1,
    "lower_tolerance": -0.1,
    "unit": "mm",
    "is_critical": false,
    "inspection_method": "卡尺",
    "gage": "游标卡尺"
}

响应 (201 Created):
{
    "id": "uuid",
    "char_number": "C51",
    "char_name": "新特性"
}
```

### 5.5 批量导入特性

```http
POST /api/v1/inspections/plans/{id}/import_characteristics/

请求体:
{
    "characteristics": [
        {
            "char_number": "C1",
            "char_name": "外径",
            "nominal_value": 50.0,
            "upper_tolerance": 0.05,
            "lower_tolerance": -0.05
        }
    ]
}

响应:
{
    "success": true,
    "imported_count": 50,
    "skipped_count": 2
}
```

### 5.6 从CAD生成特性

```http
POST /api/v1/inspections/plans/{id}/generate_from_cad/

响应:
{
    "success": true,
    "message": "从CAD生成特性成功",
    "generated_count": 50
}
```

### 5.7 提交审核

```http
POST /api/v1/inspections/plans/{id}/submit_for_review/

响应:
{
    "success": true,
    "message": "检验计划已提交审核",
    "workflow_id": "uuid"
}
```

### 5.8 批准检验计划

```http
POST /api/v1/inspections/plans/{id}/approve/

请求体:
{
    "comments": "审批通过"
}

响应:
{
    "success": true,
    "message": "检验计划已批准",
    "status": "ACTIVE"
}
```

### 5.9 拒绝检验计划

```http
POST /api/v1/inspections/plans/{id}/reject/

请求体:
{
    "comments": "拒绝原因"
}

响应:
{
    "success": true,
    "message": "检验计划已拒绝",
    "status": "DRAFT"
}
```

---

## 6. 测量数据API

### 6.1 获取测量批次列表

```http
GET /api/v1/measurements/batches/

参数:
- plan: 检验计划ID
- status: 状态过滤

响应:
{
    "count": 10,
    "results": [
        {
            "id": "uuid",
            "batch_number": "MB001",
            "plan": {
                "id": "uuid",
                "plan_number": "IP001",
                "plan_name": "检验计划1"
            },
            "equipment_type": "CMM",
            "equipment_id": "CMM-001",
            "environment_temp": 20.5,
            "environment_humidity": 45.0,
            "measured_at": "2026-03-01T14:00:00Z",
            "measured_by": {
                "id": 1,
                "username": "operator"
            },
            "status": "COMPLETED",
            "progress": 100,
            "pass_count": 48,
            "fail_count": 2
        }
    ]
}
```

### 6.2 创建测量批次

```http
POST /api/v1/measurements/batches/

请求体:
{
    "plan": "plan_uuid",
    "equipment_type": "CMM",
    "equipment_id": "CMM-001",
    "environment_temp": 20.5,
    "environment_humidity": 45.0,
    "notes": "测量备注"
}

响应 (201 Created):
{
    "id": "uuid",
    "batch_number": "MB002",
    "status": "DRAFT"
}
```

### 6.3 添加测量记录

```http
POST /api/v1/measurements/batches/{id}/add_measurement/

请求体:
{
    "characteristic_id": "char_uuid",
    "sample_number": 1,
    "measured_value": 50.02,
    "notes": "测量备注"
}

响应 (201 Created):
{
    "id": "uuid",
    "characteristic": {
        "id": "uuid",
        "char_number": "C1",
        "char_name": "外径"
    },
    "sample_number": 1,
    "measured_value": 50.02,
    "deviation": 0.02,
    "status": "PASS"
}
```

### 6.4 批量添加测量数据

```http
POST /api/v1/measurements/batches/{id}/batch_upload/

请求体:
{
    "measurements": [
        {
            "characteristic_id": "char_uuid",
            "sample_number": 1,
            "measured_value": 50.02
        },
        {
            "characteristic_id": "char_uuid",
            "sample_number": 2,
            "measured_value": 50.05
        }
    ]
}

响应:
{
    "success": true,
    "imported_count": 100,
    "pass_count": 98,
    "fail_count": 2
}
```

### 6.5 从Excel导入数据

```http
POST /api/v1/measurements/batches/{id}/import_excel/

请求体 (multipart/form-data):
- file: Excel文件

响应:
{
    "success": true,
    "imported_count": 250,
    "pass_count": 245,
    "fail_count": 5
}
```

### 6.6 获取测量记录列表

```http
GET /api/v1/measurements/records/

参数:
- batch: 批次ID
- characteristic: 特性ID
- status: 状态过滤

响应:
{
    "count": 250,
    "results": [
        {
            "id": "uuid",
            "batch": {
                "id": "uuid",
                "batch_number": "MB001"
            },
            "characteristic": {
                "id": "uuid",
                "char_number": "C1",
                "char_name": "外径",
                "nominal_value": 50.0,
                "upper_tolerance": 0.05,
                "lower_tolerance": -0.05
            },
            "sample_number": 1,
            "measured_value": 50.02,
            "deviation": 0.02,
            "status": "PASS",
            "created_at": "2026-03-01T14:00:00Z"
        }
    ]
}
```

### 6.7 计算统计数据

```http
POST /api/v1/measurements/batches/{id}/calculate_statistics/

响应:
{
    "success": true,
    "statistics": [
        {
            "characteristic": {
                "id": "uuid",
                "char_number": "C1",
                "char_name": "外径"
            },
            "sample_count": 5,
            "mean": 50.02,
            "std_dev": 0.015,
            "min_value": 50.0,
            "max_value": 50.04,
            "range_value": 0.04,
            "cp": 2.22,
            "cpk": 2.0
        }
    ]
}
```

### 6.8 完成测量批次

```http
POST /api/v1/measurements/batches/{id}/complete/

响应:
{
    "success": true,
    "message": "测量批次已完成",
    "status": "COMPLETED",
    "summary": {
        "total_count": 250,
        "pass_count": 245,
        "fail_count": 5,
        "pass_rate": 98.0
    }
}
```

---

## 7. 检验报告API

### 7.1 获取报告列表

```http
GET /api/v1/reports/reports/

参数:
- plan: 检验计划ID
- status: 状态过滤
- search: 搜索关键词

响应:
{
    "count": 15,
    "results": [
        {
            "id": "uuid",
            "report_number": "RPT001",
            "title": "首件检验报告",
            "plan": {
                "id": "uuid",
                "plan_number": "IP001"
            },
            "batch": {
                "id": "uuid",
                "batch_number": "MB001"
            },
            "standard": "AS9102",
            "conclusion": "PASS",
            "status": "PUBLISHED",
            "published_at": "2026-03-01T16:00:00Z"
        }
    ]
}
```

### 7.2 创建报告

```http
POST /api/v1/reports/reports/

请求体:
{
    "title": "首件检验报告",
    "plan": "plan_uuid",
    "batch": "batch_uuid",
    "template": "template_uuid",
    "standard": "AS9102",
    "summary": "检验摘要"
}

响应 (201 Created):
{
    "id": "uuid",
    "report_number": "RPT002",
    "title": "首件检验报告",
    "status": "DRAFT"
}
```

### 7.3 获取报告详情

```http
GET /api/v1/reports/reports/{id}/

响应:
{
    "id": "uuid",
    "report_number": "RPT001",
    "title": "首件检验报告",
    "plan": {
        "id": "uuid",
        "plan_number": "IP001",
        "plan_name": "检验计划1"
    },
    "batch": {
        "id": "uuid",
        "batch_number": "MB001"
    },
    "template": {
        "id": "uuid",
        "name": "AS9102标准模板"
    },
    "standard": "AS9102",
    "summary": "本次首件检验共测量50项特性...",
    "conclusion": "PASS",
    "status": "PUBLISHED",
    "statistics": {
        "total_characteristics": 50,
        "pass_count": 48,
        "fail_count": 2,
        "pass_rate": 96.0,
        "critical_count": 5,
        "critical_pass_count": 5
    },
    "generated_at": "2026-03-01T15:00:00Z",
    "published_at": "2026-03-01T16:00:00Z"
}
```

### 7.4 生成报告

```http
POST /api/v1/reports/reports/{id}/generate/

响应:
{
    "success": true,
    "message": "报告生成任务已启动",
    "status": "GENERATING"
}
```

### 7.5 发布报告

```http
POST /api/v1/reports/reports/{id}/publish/

请求体:
{
    "comments": "报告已审核通过"
}

响应:
{
    "success": true,
    "message": "报告已发布",
    "status": "PUBLISHED",
    "published_at": "2026-03-01T16:00:00Z"
}
```

### 7.6 下载报告

```http
GET /api/v1/reports/reports/{id}/download/

响应:
Content-Type: application/pdf
Content-Disposition: attachment; filename="RPT001.pdf"

[PDF文件内容]
```

### 7.7 获取报告模板列表

```http
GET /api/v1/reports/templates/

响应:
{
    "count": 3,
    "results": [
        {
            "id": "uuid",
            "name": "AS9102标准模板",
            "standard": "AS9102",
            "is_active": true,
            "created_at": "2026-03-01T10:00:00Z"
        }
    ]
}
```

---

## 8. 工作流管理API

### 8.1 获取工作流列表

```http
GET /api/v1/workflows/workflows/

参数:
- workflow_type: 工作流类型
- status: 状态过滤
- initiated_by: 发起人ID

响应:
{
    "count": 20,
    "results": [
        {
            "id": "uuid",
            "workflow_type": "PLAN_APPROVAL",
            "status": "IN_PROGRESS",
            "current_step": 2,
            "initiated_by": {
                "id": 1,
                "username": "engineer"
            },
            "initiated_at": "2026-03-01T10:00:00Z",
            "plan": {
                "id": "uuid",
                "plan_number": "IP001"
            }
        }
    ]
}
```

### 8.2 获取我的待审批

```http
GET /api/v1/workflows/workflows/my_pending/

响应:
{
    "count": 5,
    "results": [
        {
            "id": "uuid",
            "workflow_type": "PLAN_APPROVAL",
            "current_step": {
                "step_number": 2,
                "step_name": "审核"
            },
            "initiated_by": {
                "username": "engineer"
            },
            "initiated_at": "2026-03-01T10:00:00Z",
            "object": {
                "type": "inspection_plan",
                "id": "uuid",
                "name": "检验计划1"
            }
        }
    ]
}
```

### 8.3 审批通过

```http
POST /api/v1/workflows/workflows/{id}/approve/

请求体:
{
    "comments": "审批通过",
    "signature_image": "base64_encoded_image"
}

响应:
{
    "success": true,
    "message": "审批通过",
    "current_step": 3,
    "status": "IN_PROGRESS"
}
```

### 8.4 审批拒绝

```http
POST /api/v1/workflows/workflows/{id}/reject/

请求体:
{
    "comments": "拒绝原因：需要补充测量数据"
}

响应:
{
    "success": true,
    "message": "已拒绝",
    "status": "REJECTED"
}
```

### 8.5 获取不合格品报告列表

```http
GET /api/v1/workflows/ncr/

参数:
- status: 状态过滤
- problem_type: 问题类型过滤
- inspector: 检验人ID

响应:
{
    "count": 10,
    "results": [
        {
            "id": "uuid",
            "ncr_number": "NCR001",
            "product_name": "零件A",
            "specification": "50±0.05",
            "batch_number": "B2026001",
            "problem_type": "DIMENSION",
            "problem_description": "外径超差",
            "status": "OPEN",
            "inspector": {
                "id": 1,
                "username": "inspector"
            },
            "inspected_at": "2026-03-01T10:00:00Z",
            "actions_count": 2
        }
    ]
}
```

### 8.6 创建不合格品报告

```http
POST /api/v1/workflows/ncr/

请求体:
{
    "product_name": "零件A",
    "specification": "50±0.05",
    "batch_number": "B2026001",
    "department_code": "D001",
    "problem_type": "DIMENSION",
    "problem_description": "外径测量值50.08，超出上限",
    "defect_phenomenon": "尺寸超差",
    "supply_method": "INTERNAL",
    "supplier_name": "",
    "delivery_date": "2026-03-01",
    "notes": "备注信息"
}

响应 (201 Created):
{
    "id": "uuid",
    "ncr_number": "NCR002",
    "status": "OPEN"
}
```

### 8.7 添加处理措施

```http
POST /api/v1/workflows/ncr/{id}/add_action/

请求体:
{
    "action_type": "REWORK",
    "action_description": "返工至合格尺寸",
    "responsible_person": "user_uuid",
    "due_date": "2026-03-05"
}

响应 (201 Created):
{
    "id": "uuid",
    "action_type": "REWORK",
    "action_description": "返工至合格尺寸",
    "status": "PENDING"
}
```

### 8.8 完成处理措施

```http
POST /api/v1/workflows/ncr/actions/{id}/complete/

请求体:
{
    "completion_notes": "已完成返工，重新检验合格"
}

响应:
{
    "success": true,
    "message": "处理措施已完成",
    "status": "COMPLETED"
}
```

---

## 9. 项目管理API

### 9.1 获取项目列表

```http
GET /api/v1/core/projects/

参数:
- status: 状态过滤
- search: 搜索关键词

响应:
{
    "count": 10,
    "results": [
        {
            "id": "uuid",
            "project_number": "FAI2026001",
            "project_name": "首件检验项目A",
            "description": "项目描述",
            "status": "IN_PROGRESS",
            "progress_percentage": 60,
            "start_date": "2026-03-01",
            "target_date": "2026-03-15",
            "steps_count": 8,
            "completed_steps": 5
        }
    ]
}
```

### 9.2 创建项目

```http
POST /api/v1/core/projects/

请求体:
{
    "project_number": "FAI2026002",
    "project_name": "新项目",
    "description": "项目描述",
    "start_date": "2026-03-01",
    "target_date": "2026-03-15"
}

响应 (201 Created):
{
    "id": "uuid",
    "project_number": "FAI2026002",
    "project_name": "新项目",
    "status": "DRAFT"
}
```

### 9.3 获取项目详情

```http
GET /api/v1/core/projects/{id}/

响应:
{
    "id": "uuid",
    "project_number": "FAI2026001",
    "project_name": "首件检验项目A",
    "status": "IN_PROGRESS",
    "progress_percentage": 60,
    "steps": [
        {
            "id": "uuid",
            "step_code": "PRODUCT_INFO",
            "step_name": "产品信息",
            "step_order": 1,
            "status": "COMPLETED",
            "completed_at": "2026-03-01T10:00:00Z"
        },
        {
            "id": "uuid",
            "step_code": "DRAWING_IMPORT",
            "step_name": "图纸导入",
            "step_order": 2,
            "status": "COMPLETED",
            "completed_at": "2026-03-01T11:00:00Z"
        },
        {
            "id": "uuid",
            "step_code": "MEASUREMENT",
            "step_name": "测量数据",
            "step_order": 5,
            "status": "IN_PROGRESS",
            "completed_at": null
        }
    ]
}
```

### 9.4 完成项目步骤

```http
POST /api/v1/core/projects/{id}/complete_step/

请求体:
{
    "step_code": "MEASUREMENT",
    "notes": "测量数据已完成录入"
}

响应:
{
    "success": true,
    "message": "步骤已完成",
    "progress_percentage": 75
}
```

---

## 10. 设备管理API

### 10.1 获取设备列表

```http
GET /api/v1/equipment/api/

参数:
- equipment_type: 设备类型
- status: 状态过滤
- search: 搜索关键词

响应:
{
    "count": 20,
    "results": [
        {
            "id": "uuid",
            "equipment_id": "CMM-001",
            "name": "三坐标测量机",
            "equipment_type": "CMM",
            "manufacturer": "Zeiss",
            "model": "CONTURA",
            "serial_number": "SN12345",
            "calibration_date": "2025-12-01",
            "next_calibration_date": "2026-12-01",
            "status": "ACTIVE",
            "location": "测量室A"
        }
    ]
}
```

### 10.2 创建设备

```http
POST /api/v1/equipment/api/

请求体:
{
    "equipment_id": "CMM-002",
    "name": "三坐标测量机2",
    "equipment_type": "CMM",
    "manufacturer": "Hexagon",
    "model": "GLOBAL",
    "serial_number": "SN67890",
    "calibration_date": "2026-01-01",
    "next_calibration_date": "2027-01-01",
    "status": "ACTIVE",
    "location": "测量室B"
}

响应 (201 Created):
{
    "id": "uuid",
    "equipment_id": "CMM-002",
    "status": "ACTIVE"
}
```

---

## 11. 错误码参考

### 11.1 HTTP状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功(无返回内容) |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 405 | 方法不允许 |
| 409 | 资源冲突(如唯一性约束) |
| 500 | 服务器内部错误 |

### 11.2 业务错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| VALIDATION_ERROR | 参数验证失败 | 检查请求参数格式 |
| DUPLICATE_ERROR | 资源重复 | 检查唯一性字段 |
| STATUS_ERROR | 状态不允许该操作 | 检查资源当前状态 |
| PERMISSION_DENIED | 权限不足 | 检查用户权限 |
| FILE_UPLOAD_ERROR | 文件上传失败 | 检查文件格式和大小 |
| CAD_PARSE_ERROR | CAD解析失败 | 检查CAD文件格式 |
| REPORT_GENERATE_ERROR | 报告生成失败 | 检查数据和模板 |
| WORKFLOW_ERROR | 工作流操作失败 | 检查工作流状态 |

### 11.3 错误响应示例

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "参数验证失败",
        "details": {
            "part_number": ["该字段是必填项"],
            "fai_quantity": ["该值必须大于0"]
        }
    }
}
```

---

## 附录

### A. 请求示例 (curl)

```bash
# 登录
curl -X POST http://localhost:5000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'

# 获取零件列表
curl -X GET http://localhost:5000/api/v1/parts/api/ \
  -H "Authorization: Token your_token_here"

# 创建零件
curl -X POST http://localhost:5000/api/v1/parts/api/ \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{"part_number":"P001","part_name":"新零件"}'

# 上传文件
curl -X POST http://localhost:5000/api/v1/parts/api/{id}/upload_cad/ \
  -H "Authorization: Token your_token_here" \
  -F "cad_file=@/path/to/file.step"
```

### B. SDK示例 (Python)

```python
import requests

class FAIClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Token {token}"}
    
    def get_parts(self, **params):
        response = requests.get(
            f"{self.base_url}/api/v1/parts/api/",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def create_part(self, data):
        response = requests.post(
            f"{self.base_url}/api/v1/parts/api/",
            headers=self.headers,
            json=data
        )
        return response.json()

# 使用示例
client = FAIClient("http://localhost:5000", "your_token")
parts = client.get_parts(status="ACTIVE")
new_part = client.create_part({
    "part_number": "P001",
    "part_name": "新零件"
})
```

---

**文档版本历史**

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-03-13 | 初始版本 | FAI开发团队 |
