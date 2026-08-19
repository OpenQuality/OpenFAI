# OpenFAI 首件检验系统 — 部署手册

> 版本: v2026.08.16 | 更新: 2026年8月

---

## 目录

1. [系统概述](#1-系统概述)
2. [环境要求](#2-环境要求)
3. [宝塔面板部署（推荐）](#3-宝塔面板部署推荐)
4. [命令行部署（无面板）](#4-命令行部署无面板)
5. [初始化与演示数据](#5-初始化与演示数据)
6. [Nginx 配置参考](#6-nginx-配置参考)
7. [日常运维](#7-日常运维)
8. [常见问题](#8-常见问题)

---

## 1. 系统概述

OpenFAI 是一套基于 Django 5.2 的首件检验（FAI）质量管理系统，支持：

- 图纸 OCR 识别（AI 视觉模型 / 本地引擎）
- 检验计划与检验特性管理
- 测量数据录入与 Cp/Cpk 自动统计
- AS9102/PPAP 检验报告生成
- 多级审批工作流
- 不合格品（NCR）管理

**技术栈**

| 组件 | 版本 |
|------|------|
| Python | 3.11+（最低 3.11，推荐 3.12） |
| Django | 5.2 |
| 数据库 | SQLite（默认，无需额外安装） |
| 前端 | Bootstrap 5 + Bootstrap Icons |
| Web服务 | Gunicorn + Nginx |

---

## 2. 环境要求

### 硬件

| 项目 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB | 50 GB SSD |

### OCR 引擎与 CPU 硬件适配

> **推荐优先使用云端 AI 视觉引擎**（豆包/Kimi/GLM 等），效果远优于本地引擎，且无 CPU 架构限制。

| 本地 OCR 引擎 | 是否预装 | 效果 | Intel（AVX-512） | AMD EPYC Zen2/3 | 说明 |
|--------------|:------:|------|:-:|:-:|------|
| **RapidOCR** ✅ | **默认预装** | ⭐⭐⭐ | ✅ | ✅ | 基于 ONNX Runtime，无 CPU 指令集限制，开箱即用 |
| **PaddleOCR** | 可选安装 | ⭐⭐⭐ | ✅ | ❌ SIGILL | 需 AVX-512 + 手动安装，见 §8.5；AMD 服务器禁止使用 |
| **百度 OCR** | 无需安装 | ⭐⭐⭐⭐ | ✅ | ✅ | 云端 REST API，需 API Key，见「引擎配置」页面 |

**如何判断 CPU 是否支持 AVX-512（仅用于决定是否安装 PaddleOCR）：**
```bash
grep -o 'avx512[^ ]*' /proc/cpuinfo | sort -u
# 有输出 = 支持 AVX-512，可选安装 PaddleOCR（见 §8.5）
# 无输出 = 不支持，保持默认 RapidOCR 即可
```

### 软件

- 操作系统：Ubuntu 20.04/22.04/24.04 LTS 或 CentOS 7/8
- **Python 3.11+**（最低要求；Django 5.2 不支持 3.10 及以下版本）
- Nginx 1.18+

---

## 3. 宝塔面板部署（推荐）

### 3.1 准备工作

登录宝塔面板，在**软件商店**确认已安装：

- **Nginx**
- **Python 项目管理器**（管理虚拟环境和 Gunicorn 进程）

### 3.2 上传并解压代码

**方法一：文件管理器**

1. 宝塔 → **文件** → 进入 `/www/wwwroot/`
2. 点击**上传** → 选择 `project-V7.tar.gz`
3. 上传完成后右键 → **解压** → 解压到 `/www/wwwroot/OpenFAI`

**方法二：SSH 命令**

```bash
cd /www/wwwroot
mkdir OpenFAI && cd OpenFAI
tar -xzf /path/to/project-V7.tar.gz --strip-components=1
```

### 3.3 创建虚拟环境并安装依赖

通过宝塔**终端**或 SSH 执行：

```bash
cd /www/wwwroot/OpenFAI

# 创建虚拟环境（需 Python 3.11+）
python3 -m venv venv
source venv/bin/activate

# 更新 pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖（RapidOCR / OpenCV 需要）
apt-get install -y libgl1 libglib2.0-0

# 安装依赖（已含 RapidOCR，开箱即用）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 确保使用无头版 OpenCV（服务器无显示器，避免 libGL 报错）
pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
pip install --force-reinstall --no-deps opencv-python-headless \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3.4 初始化数据库

```bash
cd /www/wwwroot/OpenFAI
source venv/bin/activate

# 执行数据库迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 创建管理员账号
python manage.py createsuperuser
```

> 数据库默认使用 SQLite（`db.sqlite3`），无需额外安装和配置，开箱即用。

### 3.5 配置 Gunicorn

**方式一：宝塔 Python 项目管理器（推荐）**

宝塔 → **Python 项目** → **添加项目**，填写：

| 项目 | 值 |
|------|----|
| 项目名称 | OpenFAI |
| 项目路径 | `/www/wwwroot/OpenFAI` |
| Python版本 | 3.10 或以上 |
| 启动模块 | `fai_system.wsgi:application` |
| 端口 | `5000` |
| Worker数量 | `3` |

点击**确定**，宝塔自动启动 Gunicorn 进程。

**方式二：Supervisor（宝塔插件）**

宝塔 → **软件商店** → 安装 **Supervisor**，添加守护进程：

```ini
[program:openfai]
directory=/www/wwwroot/OpenFAI
command=/www/wwwroot/OpenFAI/venv/bin/gunicorn
    --workers 3
    --bind 127.0.0.1:5000
    --timeout 300
    --access-logfile /www/wwwlogs/openfai_access.log
    --error-logfile /www/wwwlogs/openfai_error.log
    fai_system.wsgi:application
user=www
autostart=true
autorestart=true
redirect_stderr=true
```

> **超时说明**：`--timeout 300` 与 Nginx `proxy_read_timeout 300s` 保持一致。云端 AI 视觉引擎（豆包/Kimi/GLM）识别复杂图纸可能需要 60~120 秒，设置过短（如 120s）会导致 Gunicorn worker 被强制杀掉并返回 502 错误。

### 3.6 配置 Nginx 反向代理

1. 宝塔 → **网站** → **添加站点**，填写域名，PHP版本选**纯静态**
2. 进入站点**设置** → **配置文件**，在 `server {}` 块内添加：

```nginx
# 静态文件（直接由 Nginx 响应，不经过 Gunicorn）
location /static/ {
    alias /www/wwwroot/OpenFAI/staticfiles/;
    expires 30d;
}

# 用户上传文件
location /media/ {
    alias /www/wwwroot/OpenFAI/media/;
    expires 7d;
}

# 应用代理
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 300s;
    proxy_read_timeout 300s;
    client_max_body_size 100M;
}
```

3. **保存** → **重启 Nginx**

4. 如需 HTTPS：站点设置 → **SSL** → 申请 Let's Encrypt 免费证书

### 3.7 设置目录权限

```bash
chown -R www:www /www/wwwroot/OpenFAI
chmod -R 755 /www/wwwroot/OpenFAI
# media 目录需要写入权限（用于用户上传文件）
mkdir -p /www/wwwroot/OpenFAI/media
chmod -R 775 /www/wwwroot/OpenFAI/media

# ⚠️ 修复 Gunicorn 可执行权限（宝塔部署必须执行，否则重启报 Permission denied）
chmod +x /www/wwwroot/OpenFAI/venv/bin/python3
chmod +x /www/wwwroot/OpenFAI/venv/bin/gunicorn
```

### 3.8 开放防火墙

宝塔 → **安全** → **防火墙**，放行端口：

- `80`（HTTP）
- `443`（HTTPS，如启用 SSL）

> 5000 端口为内部 Gunicorn 端口，**不需要**对外开放。

---

## 4. 命令行部署（无面板）

### 4.1 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
    nginx libgl1 libglib2.0-0

# CentOS/RHEL
sudo yum install -y python3 python3-pip nginx mesa-libGL
```

### 4.2 解压代码

```bash
mkdir -p /var/www/OpenFAI
tar -xzf project-V7.tar.gz -C /var/www/OpenFAI --strip-components=1
cd /var/www/OpenFAI
```

### 4.3 虚拟环境与依赖

```bash
python3 -m venv venv
source venv/bin/activate

# 更新 pip
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装依赖（已含 RapidOCR）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 确保使用无头版 OpenCV
pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
pip install --force-reinstall --no-deps opencv-python-headless \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.4 初始化

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 4.5 配置 systemd 服务

```bash
sudo tee /etc/systemd/system/openfai.service > /dev/null <<'EOF'
[Unit]
Description=OpenFAI Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/OpenFAI
ExecStart=/var/www/OpenFAI/venv/bin/gunicorn \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind unix:/run/openfai.sock \
    --timeout 300 \
    --access-logfile /var/log/openfai/access.log \
    --error-logfile /var/log/openfai/error.log \
    fai_system.asgi:application
RuntimeDirectory=openfai
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable openfai
sudo systemctl start openfai
```

### 4.6 Nginx 配置

```bash
sudo tee /etc/nginx/sites-available/openfai > /dev/null <<'EOF'
server {
    listen 80;
    server_name 你的域名或IP;

    location /static/ {
        alias /var/www/OpenFAI/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/OpenFAI/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
        proxy_connect_timeout 300s;
        proxy_read_timeout    300s;
        proxy_send_timeout    300s;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/openfai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. 初始化与演示数据

### 5.1 创建管理员

```bash
source venv/bin/activate
python manage.py createsuperuser
```

### 5.2 一键生成演示数据

```bash
bash init_demo.sh
```

演示数据包含：

| 类型 | 数量 | 说明 |
|------|------|------|
| 零件 | 4 个 | 航空叶片、液压阀体、传动轴、卫星框架 |
| FAI 项目 | 4 个 | 不同进度阶段（完成/进行中/草稿） |
| SOP 文档 | 3 个 | 检验指导书、SOP、控制计划 |
| 检验计划 | 4 个 | 含 21 项检验特性 |
| 测量记录 | 161 条 | 含 30 条 Cpk 统计 |
| 检验报告 | 2 份 | 一份已发布、一份草稿 |
| NCR 报告 | 1 个 | 密封槽超差示例 |

**演示账号：**

| 用户名 | 密码 | 角色 |
|--------|------|------|
| `admin` | `admin123` | 管理员 |
| `inspector1` | `demo123` | 质量检验员 |
| `reviewer1` | `demo123` | 质量审核员 |
| `approver1` | `demo123` | 质量经理 |
| `engineer1` | `demo123` | 质量工程师 |

> `init_demo.sh` 是幂等的，重复执行不会产生重复数据。

---

## 6. Nginx 配置参考

### 宝塔站点完整配置（含 SSL）

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # 宝塔自动填写 SSL 证书路径
    ssl_certificate    /www/server/panel/vhost/cert/your-domain.com/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location /static/ {
        alias /www/wwwroot/OpenFAI/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias /www/wwwroot/OpenFAI/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }

    access_log  /www/wwwlogs/openfai.access.log;
    error_log   /www/wwwlogs/openfai.error.log;
}
```

---

## 7. 日常运维

### 服务管理

```bash
# Supervisor
supervisorctl status openfai
supervisorctl restart openfai

# systemd
sudo systemctl status openfai
sudo systemctl restart openfai

# 查看日志
tail -100f /www/wwwlogs/openfai_error.log
```

### 数据库备份（SQLite）

```bash
# 手动备份
cp /www/wwwroot/OpenFAI/db.sqlite3 /backup/fai_$(date +%Y%m%d).db

# 定时备份（crontab -e）
0 3 * * * cp /www/wwwroot/OpenFAI/db.sqlite3 /backup/fai_$(date +\%Y\%m\%d).db
```

### 更新部署

```bash
cd /www/wwwroot/OpenFAI
source venv/bin/activate

# 替换代码文件后执行
python manage.py migrate          # 有新迁移时执行
python manage.py collectstatic --noinput
supervisorctl restart openfai     # 或 systemctl restart openfai
```

---

## 8. 常见问题

### 8.1 静态文件（CSS/JS）加载失败
```bash
python manage.py collectstatic --noinput
# 检查 Nginx alias 路径末尾是否有斜杠
```

### 8.2 页面 500 错误
```bash
tail -50 /www/wwwlogs/openfai_error.log
```

### 8.3 上传文件失败
```bash
chown -R www:www /www/wwwroot/OpenFAI/media
chmod -R 775 /www/wwwroot/OpenFAI/media
```

### 8.4 Gunicorn 重启报 Permission denied
```bash
chmod +x /www/wwwroot/OpenFAI/venv/bin/python3
chmod +x /www/wwwroot/OpenFAI/venv/bin/gunicorn
```

### 8.5 PaddleOCR 可选安装（仅限 Intel AVX-512 服务器）

> ⚠️ **V7 起默认不预装 PaddleOCR**。系统开箱使用 RapidOCR，绝大多数场景下已足够。  
> 若需在 Intel Xeon/Core 高性能服务器上使用 PaddleOCR，按以下步骤手动安装：

**安装前确认 CPU 支持 AVX-512：**
```bash
grep -o 'avx512[^ ]*' /proc/cpuinfo | sort -u
# 必须有输出才能安装 PaddleOCR，否则会 SIGILL 崩溃
```

**安装步骤：**
```bash
source venv/bin/activate
pip install paddlepaddle>=2.6.0 paddleocr>=2.7.0,<3.0.0 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 修复 opencv 冲突（PaddleOCR 会拉入 opencv-python，需换回 headless 版）
pip uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
pip install --force-reinstall --no-deps opencv-python-headless \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 修复模型缓存目录权限（宝塔 www 用户无法写 /root）
mkdir -p /www/wwwroot/OpenFAI/.paddleocr
chown -R www:www /www/wwwroot/OpenFAI/.paddleocr

systemctl restart openfai
```

安装完成后，在页面「系统管理 → 引擎配置」的引擎下拉框中选择 **PaddleOCR（本地）** 即可使用。

**AMD EPYC Zen2/3 CPU 禁止安装 PaddleOCR**（SIGILL 崩溃根因）：

PaddleOCR 2.6.x 的 `SelfAttentionFusePass` 编译了 AVX-512 指令，AMD EPYC Zen2（7K62、7002、7003 系列）仅支持 AVX2，运行时触发 `Illegal instruction`（exit code 132），Gunicorn worker 崩溃。三个 paddle 构建版本（标准版/noavx/openblas）均受影响，**无解，请使用 RapidOCR**。

### 8.6 CSRF 验证失败

在 `settings.py` 末尾添加：
```python
CSRF_TRUSTED_ORIGINS = ['https://你的域名', 'http://你的域名']
```

---

*文档版本: v2026.08.16 | OpenFAI 开发团队*
