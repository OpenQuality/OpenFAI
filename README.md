# FAI（首件检验）自动化质量评审系统

> 版本: v2026.08.16 | 更新日期: 2026年8月

---

## 系统概述

FAI（First Article Inspection，首件检验）自动化质量评审系统是一款专业的质量管理软件，支持：

- **图纸智能识别**：使用AI视觉模型自动识别图纸中的尺寸标注和公差信息
- **检验计划管理**：从CAD文件解析或手动创建检验计划
- **测量数据采集**：支持多种测量设备集成，自动采集测量数据
- **统计分析**：自动计算Cp/Cpk等过程能力指标
- **报告生成**：生成符合AS9102/PPAP标准的检验报告
- **审批工作流**：支持电子签名和多级审批流程

### 支持的标准

- **AS9102**：航空航天首件检验标准
- **PPAP**：生产件批准程序
- **ISO 9001**：质量管理体系

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Django 5.2 + Django REST Framework 3.15.2 |
| 数据库 | PostgreSQL (生产) / SQLite (开发) |
| 前端 | Bootstrap 5 + Bootstrap Icons |
| 文件存储 | S3兼容对象存储（boto3） |
| PDF处理 | PyMuPDF |
| OCR | 云端 AI 视觉模型（推荐）/ PaddleOCR / RapidOCR |

---

## 快速开始

### OCR 引擎选择（重要）

> **云端 AI 视觉模型识别效果远优于本地引擎**，推荐优先配置云端引擎（豆包/Kimi/GLM 等），在「系统管理 → 引擎配置」中填写 API Key 即可。本地引擎作为无网络时的离线备选。

| OCR 引擎 | 适用 CPU | 安装包 | 效果 | 说明 |
|----------|----------|--------|------|------|
| **云端 AI**（推荐） | 任意 | 无需安装 | ⭐⭐⭐⭐⭐ | 需 API Key，识别精度最高 |
| **RapidOCR** | 任意（含 AMD EPYC Zen2） | `rapidocr-onnxruntime` | ⭐⭐⭐ | ONNX Runtime，无 AVX-512 依赖，AMD CPU 首选 |
| **PaddleOCR** | Intel AVX-512+ | `paddlepaddle paddleocr` | ⭐⭐⭐ | 需 AVX-512，AMD EPYC Zen2 会 SIGILL 崩溃 |
| **百度 OCR** | 任意 | 无需安装 | ⭐⭐⭐⭐ | 需百度云 API Key，按量计费 |

**CPU 兼容性快速参考：**

| CPU 系列 | AVX-512 | PaddleOCR | RapidOCR |
|----------|---------|-----------|----------|
| Intel Xeon Gold/Platinum（Skylake+） | ✅ | ✅ | ✅ |
| Intel Core 12代+ | ✅ | ✅ | ✅ |
| AMD EPYC Zen2/3（7K62、7002、7003） | ❌ | ❌ SIGILL | ✅ |
| AMD Ryzen 5000 以下 | ❌ | ❌ SIGILL | ✅ |

### 环境要求

- Python 3.11+（最低要求；推荐 3.12）
- PostgreSQL 14+（生产环境，开发用 SQLite 无需安装）

### 安装部署

```bash
# 安装依赖（含 RapidOCR，开箱即用；PaddleOCR 需 Intel AVX-512 CPU，见部署文档 §8.5）
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建管理员
python manage.py createsuperuser

# 启动服务
python manage.py runserver 0.0.0.0:5000
```

### 访问系统

- 系统地址: http://localhost:5000
- 管理后台: http://localhost:5000/admin/

### 默认账号

- 管理员: `admin` / `admin123`

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层 (Browser)                          │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Nginx (反向代理/负载均衡)                     │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django Application Server                     │
│                     Gunicorn (端口: 5000)                        │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │      Redis       │  │   S3 Storage     │
│   (主数据库)      │  │  (缓存/队列)      │  │   (文件存储)      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 功能模块

| 模块 | 功能描述 |
|------|----------|
| 仪表盘 | 系统概览，关键统计数据，快速操作入口 |
| 零件管理 | 零件信息维护、CAD文件上传、图纸管理 |
| OCR识别 | 图纸自动识别，尺寸提取，公差解析 |
| 检验计划 | 检验计划创建、特性定义、CAD解析生成 |
| SOP管理 | 标准作业程序、检验指导书、控制计划 |
| 测量批次 | 测量批次管理、数据录入、Cp/Cpk自动计算 |
| 统计分析 | 过程能力分析、直方图、控制图、趋势图 |
| 检验报告 | 报告生成、PDF导出、AS9102/PPAP标准 |
| 项目管理 | FAI项目跟踪、步骤管理、进度监控 |
| 审批流程 | 多级审批、电子签名、流程管理 |
| 设备集成 | 测量设备接口、数据采集 |

---

## 典型工作流程

```
零件管理 → OCR识别 → 检验计划 → SOP(检验指导书) → 测量批次 → 统计分析(Cp/Cpk) → 检验报告 → 审批流程
   │              │            │              │              │                │              │
   ▼              ▼            ▼              ▼              ▼                ▼              ▼
 创建零件      自动提取尺寸    定义检验项目    关联作业指导     录入数据        自动计算       生成标准报告
 上传图纸      识别公差       设置公差       控制计划        自动判定        Cp/Cpk等      AS9102/PPAP
```

### Cp/Cpk 判定标准

| Cpk 范围 | 判定 | 说明 |
|----------|------|------|
| Cpk ≥ 1.67 | 优秀 | 过程能力充足 |
| 1.33 ≤ Cpk < 1.67 | 良好 | 满足要求 |
| 1.00 ≤ Cpk < 1.33 | 合格 | 需要改进 |
| Cpk < 1.00 | 不合格 | 需采取措施 |
8. 发布报告 ← 7. 审批 ← 6. 生成报告 ← 5. 录入测量数据
```

---

## 界面导航

系统左侧导航栏包含以下主要功能：

| 菜单项 | 功能说明 |
|--------|----------|
| 仪表盘 | 系统概览，显示关键统计数据 |
| 零件管理 | 管理零件信息、上传图纸 |
| 检验计划 | 创建和管理检验计划 |
| 测量批次 | 管理测量数据和统计分析 |
| 检验报告 | 生成和管理检验报告 |
| 审批流程 | 管理审批工作流 |
| 项目管理 | 管理FAI项目 |
| 设备管理 | 管理测量设备 |
| 用户管理 | 用户和角色管理（管理员） |
| 系统设置 | OCR引擎配置等系统设置 |

### 侧边栏折叠功能

- **折叠侧边栏**：点击侧边栏顶部的折叠按钮，侧边栏将收缩为仅显示图标
- **展开侧边栏**：再次点击折叠按钮恢复完整显示
- **状态记忆**：折叠状态自动保存，刷新页面后保持原状态

---

## 权限角色

| 角色 | 权限范围 |
|------|----------|
| 管理员 (ADMIN) | 全部模块 |
| 批准人 (APPROVER) | reports, workflows |
| 审核员 (REVIEWER) | inspections, reports, workflows |
| 检验员 (INSPECTOR) | measurements, inspections(view) |
| 质量工程师 (QUALITY_ENGINEER) | inspections, measurements, reports |
| 质量经理 (QUALITY_MANAGER) | 全部模块(view/edit) |
| 查看者 (VIEWER) | 全部模块(view) |

---

## 技术文档

详细技术文档请参考 `docs/` 目录：

| 文档 | 说明 |
|------|------|
| [docs/WORKFLOW_OVERVIEW.md](docs/WORKFLOW_OVERVIEW.md) | 系统工作流程与 Cp/Cpk 说明 |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | 部署指南 |
| [docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md) | 运维手册 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API接口文档 |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | 数据库设计 |
| [docs/CAD_SUPPORT.md](docs/CAD_SUPPORT.md) | CAD文件支持说明 |

---

## 常见问题

### OCR引擎状态不更新

安装完成后按 F5 刷新页面。

### PaddleOCR 在 AMD CPU 上崩溃（SIGILL）

AMD EPYC Zen2/3 及部分 Ryzen 处理器不支持 AVX-512，PaddleOCR 初始化时会触发 SIGILL 导致 Gunicorn worker 崩溃。

**解决方案：卸载 PaddleOCR，改用 RapidOCR：**
```bash
source venv/bin/activate
pip uninstall -y paddlepaddle paddleocr
apt-get install -y libgl1 libglib2.0-0
pip install rapidocr-onnxruntime
```
RapidOCR 基于 ONNX Runtime，与 CPU 指令集无关，AMD 和 Intel 均可正常运行。

### PaddleOCR导入失败（libGL 缺失）

```bash
apt-get install -y libgl1 libglib2.0-0
```

### 数据库连接失败

检查 `DATABASE_URL` 环境变量配置。

---

## 项目结构

```
/workspace/projects/
├── fai_system/          # Django项目配置
├── accounts/            # 用户权限模块
├── core/                # 核心功能
├── parts/               # 零件管理
├── inspections/         # 检验计划
├── measurements/         # 测量数据
├── reports/             # 报告生成
├── workflows/           # 工作流管理
├── equipment/           # 设备管理
├── templates/           # 模板文件
├── docs/                # 技术文档
├── requirements.txt     # Python依赖
├── manage.py            # Django管理脚本
└── DEPLOYMENT_CONFIG.toml  # 详细部署配置
```
