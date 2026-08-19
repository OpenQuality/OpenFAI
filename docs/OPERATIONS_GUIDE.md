# FAI系统运维手册

> 版本: 1.0.0  
> 更新日期: 2026年3月

---

## 目录

1. [日常运维](#1-日常运维)
2. [监控告警](#2-监控告警)
3. [日志管理](#3-日志管理)
4. [备份恢复](#4-备份恢复)
5. [性能优化](#5-性能优化)
6. [安全运维](#6-安全运维)
7. [故障排除](#7-故障排除)
8. [应急响应](#8-应急响应)

---

## 1. 日常运维

### 1.1 服务管理

#### 启动服务

```bash
# 启动所有服务
sudo supervisorctl start all

# 启动单个服务
sudo supervisorctl start fai_system
sudo supervisorctl start fai_celery
sudo supervisorctl start fai_celery_beat

# 通过systemctl管理
sudo systemctl start nginx
sudo systemctl start postgresql
sudo systemctl start redis-server
```

#### 停止服务

```bash
# 停止所有服务
sudo supervisorctl stop all

# 停止单个服务
sudo supervisorctl stop fai_system

# 优雅停止
sudo supervisorctl stop fai_system
```

#### 重启服务

```bash
# 重启所有服务
sudo supervisorctl restart all

# 重启单个服务
sudo supervisorctl restart fai_system
```

#### 查看服务状态

```bash
# Supervisor服务状态
sudo supervisorctl status

# 输出示例:
# fai_system                      RUNNING   pid 12345, uptime 1:23:45
# fai_celery                      RUNNING   pid 12346, uptime 1:23:45
# fai_celery_beat                 RUNNING   pid 12347, uptime 1:23:45

# 检查端口监听
ss -tuln | grep -E ':(5000|5432|6379|80|443)'

# 检查进程
ps aux | grep -E 'gunicorn|celery|nginx'
```

### 1.2 定时任务

#### 系统定时任务 (crontab)

```bash
# 编辑定时任务
sudo crontab -e

# 定时任务配置
# 每天凌晨2点备份数据库
0 2 * * * /var/www/fai_system/scripts/backup_db.sh >> /var/log/fai_system/backup.log 2>&1

# 每周日凌晨3点清理日志
0 3 * * 0 /var/www/fai_system/scripts/cleanup_logs.sh >> /var/log/fai_system/cleanup.log 2>&1

# 每小时检查服务状态
0 * * * * /var/www/fai_system/scripts/health_check.sh >> /var/log/fai_system/health.log 2>&1

# 每天凌晨4点清理过期会话
0 4 * * * cd /var/www/fai_system && /var/www/fai_system/venv/bin/python manage.py clearsessions >> /var/log/fai_system/cleanup.log 2>&1
```

#### Celery定时任务 (beat)

```python
# fai_system/celery.py

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # 每天凌晨1点生成日报
    'generate-daily-report': {
        'task': 'reports.tasks.generate_daily_report',
        'schedule': crontab(hour=1, minute=0),
    },
    # 每小时检查设备校准状态
    'check-equipment-calibration': {
        'task': 'equipment.tasks.check_calibration',
        'schedule': crontab(minute=0),
    },
    # 每周一发送待处理提醒
    'send-pending-reminder': {
        'task': 'workflows.tasks.send_pending_reminders',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),
    },
}
```

### 1.3 数据库维护

```bash
# 连接数据库
psql -U fai_user -d fai_system

# 分析表统计信息
ANALYZE;

# 清理和分析
VACUUM ANALYZE;

# 全量清理 (需要维护窗口)
VACUUM FULL;

# 重建索引
REINDEX DATABASE fai_system;

# 检查表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# 检查连接数
SELECT count(*) FROM pg_stat_activity;

# 终止空闲连接
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND query_start < NOW() - INTERVAL '1 hour';
```

### 1.4 Redis维护

```bash
# 连接Redis
redis-cli -a your_password

# 查看内存使用
INFO memory

# 查看所有键
KEYS *

# 查看键数量
DBSIZE

# 清空缓存 (谨慎使用)
FLUSHDB

# 查看慢查询
SLOWLOG GET 10

# 检查连接数
CLIENT LIST
```

---

## 2. 监控告警

### 2.1 监控指标

#### 应用监控

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 应用响应时间 | > 2秒 | 页面响应慢 |
| 错误率 | > 5% | 错误请求占比 |
| 请求数 | > 1000/秒 | 并发过高 |
| 进程内存 | > 80% | 内存使用率高 |

#### 数据库监控

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| 连接数 | > 80% max_connections | 连接数过高 |
| 慢查询数 | > 10/分钟 | 慢查询过多 |
| 表膨胀率 | > 20% | 需要VACUUM |
| 磁盘使用 | > 80% | 磁盘空间不足 |

#### 系统监控

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| CPU使用率 | > 80% | CPU负载高 |
| 内存使用率 | > 90% | 内存不足 |
| 磁盘使用率 | > 85% | 磁盘空间不足 |
| 网络带宽 | > 80% | 网络拥堵 |

### 2.2 监控脚本

#### 健康检查脚本

```bash
#!/bin/bash
# scripts/health_check.sh

LOG_FILE="/var/log/fai_system/health.log"
ALERT_EMAIL="admin@example.com"

# 检查应用
check_app() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health/)
    if [ "$response" != "200" ]; then
        echo "[$(date)] ERROR: Application health check failed (HTTP $response)" >> $LOG_FILE
        echo "FAI系统应用异常 (HTTP $response)" | mail -s "FAI系统告警" $ALERT_EMAIL
    fi
}

# 检查数据库
check_db() {
    if ! pg_isready -U fai_user -h localhost > /dev/null 2>&1; then
        echo "[$(date)] ERROR: Database connection failed" >> $LOG_FILE
        echo "FAI系统数据库连接失败" | mail -s "FAI系统告警" $ALERT_EMAIL
    fi
}

# 检查Redis
check_redis() {
    if ! redis-cli -a your_password ping > /dev/null 2>&1; then
        echo "[$(date)] ERROR: Redis connection failed" >> $LOG_FILE
        echo "FAI系统Redis连接失败" | mail -s "FAI系统告警" $ALERT_EMAIL
    fi
}

# 检查磁盘
check_disk() {
    usage=$(df -h /var | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$usage" -gt 85 ]; then
        echo "[$(date)] WARNING: Disk usage is ${usage}%" >> $LOG_FILE
        echo "FAI系统磁盘使用率 ${usage}%" | mail -s "FAI系统告警" $ALERT_EMAIL
    fi
}

# 执行检查
check_app
check_db
check_redis
check_disk
```

### 2.3 Prometheus监控配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'fai_system'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics/'
```

```yaml
# alerts.yml
groups:
  - name: fai_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率告警"
          description: "错误率超过5%"

      - alert: SlowResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过慢"
          description: "95%请求响应时间超过2秒"

      - alert: DatabaseConnections
        expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据库连接数过高"
          description: "数据库连接数超过80%"
```

---

## 3. 日志管理

### 3.1 日志文件位置

| 日志文件 | 位置 | 说明 |
|----------|------|------|
| 应用日志 | /var/log/fai_system/app.log | Django应用日志 |
| 访问日志 | /var/log/fai_system/access.log | HTTP访问日志 |
| 错误日志 | /var/log/fai_system/error.log | Gunicorn错误日志 |
| Nginx访问 | /var/log/nginx/fai_access.log | Nginx访问日志 |
| Nginx错误 | /var/log/nginx/fai_error.log | Nginx错误日志 |
| Celery日志 | /var/log/fai_system/celery.log | Celery任务日志 |
| 数据库日志 | /var/log/postgresql/ | PostgreSQL日志 |

### 3.2 日志配置

```python
# settings.py 日志配置

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/fai_system/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/fai_system/error.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'fai_system': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 3.3 日志分析命令

```bash
# 查看最近错误
tail -100 /var/log/fai_system/error.log

# 实时查看日志
tail -f /var/log/fai_system/app.log

# 搜索错误
grep -i "error\|exception\|traceback" /var/log/fai_system/app.log | tail -50

# 统计错误类型
grep -o "ERROR\|WARNING\|INFO" /var/log/fai_system/app.log | sort | uniq -c

# 分析慢请求
awk '$NF > 1000 {print $0}' /var/log/nginx/fai_access.log

# 统计访问量
awk '{print $4}' /var/log/nginx/fai_access.log | cut -d: -f1 | sort | uniq -c

# 清理日志脚本
#!/bin/bash
# scripts/cleanup_logs.sh

LOG_DIR="/var/log/fai_system"
DAYS_TO_KEEP=30

find $LOG_DIR -name "*.log" -type f -mtime +$DAYS_TO_KEEP -delete
find $LOG_DIR -name "*.log.*" -type f -mtime +$DAYS_TO_KEEP -delete

echo "[$(date)] Cleaned up logs older than $DAYS_TO_KEEP days" >> $LOG_DIR/cleanup.log
```

---

## 4. 备份恢复

### 4.1 数据库备份

#### 自动备份脚本

```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/backup/database"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/fai_system_${DATE}.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -U fai_user -h localhost -d fai_system > $BACKUP_FILE

# 压缩备份
gzip $BACKUP_FILE

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -type f -mtime +7 -delete

echo "[$(date)] Database backup completed: ${BACKUP_FILE}.gz" >> /var/log/fai_system/backup.log
```

#### 备份策略

| 备份类型 | 频率 | 保留时间 | 说明 |
|----------|------|----------|------|
| 全量备份 | 每天 | 7天 | 完整数据库备份 |
| 增量备份 | 每小时 | 24小时 | WAL日志备份 |
| 归档备份 | 每周 | 4周 | 长期保存备份 |

### 4.2 数据库恢复

```bash
# 恢复数据库
# 1. 停止应用
sudo supervisorctl stop fai_system

# 2. 解压备份文件
gunzip fai_system_20260313.sql.gz

# 3. 恢复数据库
psql -U fai_user -h localhost -d fai_system < fai_system_20260313.sql

# 4. 启动应用
sudo supervisorctl start fai_system

# 5. 验证数据
psql -U fai_user -d fai_system -c "SELECT COUNT(*) FROM parts;"
```

### 4.3 文件备份

```bash
#!/bin/bash
# scripts/backup_files.sh

BACKUP_DIR="/backup/files"
DATE=$(date +%Y%m%d)
SOURCE_DIR="/var/www/fai_system/media"

# 同步文件到备份目录
rsync -av --delete $SOURCE_DIR/ ${BACKUP_DIR}/${DATE}/

# 删除30天前的备份
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} \;

echo "[$(date)] Files backup completed" >> /var/log/fai_system/backup.log
```

### 4.4 时间点恢复 (PITR)

```bash
# 启用WAL归档 (postgresql.conf)
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'

# 基础备份
pg_basebackup -U postgres -D /backup/base -Ft -z -P

# 恢复到指定时间点
# 1. 停止PostgreSQL
sudo systemctl stop postgresql

# 2. 恢复基础备份
tar -xf /backup/base/base.tar.gz -C /var/lib/postgresql/14/main

# 3. 创建恢复配置
cat > /var/lib/postgresql/14/main/recovery.signal << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '2026-03-13 12:00:00'
EOF

# 4. 启动PostgreSQL
sudo systemctl start postgresql
```

---

## 5. 性能优化

### 5.1 数据库优化

#### PostgreSQL配置优化

```ini
# postgresql.conf

# 连接设置
max_connections = 200
superuser_reserved_connections = 3

# 内存设置
shared_buffers = 2GB
work_mem = 64MB
maintenance_work_mem = 512MB
effective_cache_size = 6GB

# 查询优化
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 100

# WAL设置
wal_buffers = 64MB
checkpoint_completion_target = 0.9
max_wal_size = 2GB

# 日志设置
log_min_duration_statement = 1000  # 记录超过1秒的查询
log_checkpoints = on
log_connections = on
log_disconnections = on
```

#### 索引优化

```sql
-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM parts WHERE part_number = 'P001';

-- 查找缺失索引
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- 查找未使用的索引
SELECT 
    schemaname || '.' || relname AS table,
    indexrelname AS index,
    pg_size_pretty(pg_relation_size(i.indexrelid)) AS index_size,
    idx_scan as index_scans
FROM pg_stat_user_indexes ui
JOIN pg_index i ON ui.indexrelid = i.indexrelid
WHERE NOT indisunique 
AND idx_scan < 50 
AND pg_relation_size(relid) > 5 * 8192
ORDER BY pg_relation_size(i.indexrelid) DESC;
```

### 5.2 应用优化

#### Gunicorn优化

```bash
# /etc/supervisor/conf.d/fai_system.conf
[program:fai_system]
command=/var/www/fai_system/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --threads 2 \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /var/log/fai_system/access.log \
    --error-logfile /var/log/fai_system/error.log \
    --log-level info \
    fai_system.wsgi:application
```

#### Django优化

```python
# settings.py

# 数据库连接池
DATABASES['default']['CONN_MAX_AGE'] = 600

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://:password@localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 查询优化 - 使用 select_related 和 prefetch_related
# 在视图中:
# queryset = Part.objects.select_related('created_by').prefetch_related('inspection_plans')

# 静态文件压缩 (使用 WhiteNoise)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ...
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 5.3 Nginx优化

```nginx
# nginx.conf

worker_processes auto;
worker_connections 1024;
multi_accept on;
use epoll;

http {
    # 缓冲区设置
    client_body_buffer_size 16K;
    client_header_buffer_size 1k;
    client_max_body_size 100M;

    # 文件缓存
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/javascript application/json application/xml;

    # 代理缓冲
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
}
```

---

## 6. 安全运维

### 6.1 安全检查清单

- [ ] DEBUG=False (生产环境)
- [ ] SECRET_KEY已更改且足够复杂
- [ ] ALLOWED_HOSTS已正确配置
- [ ] HTTPS已启用，SSL证书有效
- [ ] CSRF_COOKIE_SECURE=True
- [ ] SESSION_COOKIE_SECURE=True
- [ ] 数据库密码强度足够
- [ ] Redis密码已设置
- [ ] 防火墙规则正确配置
- [ ] 定期更新系统和依赖包
- [ ] 备份策略已实施并验证
- [ ] 日志监控已配置
- [ ] 敏感信息不在代码中硬编码

### 6.2 防火墙配置

```bash
# UFW防火墙配置
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow ssh

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 限制内部服务访问 (仅本地)
# 不允许外部访问5000, 5432, 6379端口

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status verbose
```

### 6.3 安全更新

```bash
# 更新系统
sudo apt update
sudo apt upgrade

# 更新Python依赖
cd /var/www/fai_system
source venv/bin/activate
pip install --upgrade pip
pip list --outdated
pip install -r requirements.txt --upgrade

# 检查安全漏洞
pip install safety
safety check

# 重启服务
sudo supervisorctl restart all
```

### 6.4 访问控制

```python
# settings.py 安全配置

# 安全头
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Cookie安全
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# SSL重定向
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

## 7. 故障排除

### 7.1 常见问题排查

#### 应用无法启动

```bash
# 1. 检查日志
tail -50 /var/log/fai_system/error.log

# 2. 检查Python错误
cd /var/www/fai_system
source venv/bin/activate
python manage.py check

# 3. 检查数据库连接
python manage.py dbshell

# 4. 检查配置文件
python -c "import settings; print(settings.DATABASES)"
```

#### 数据库连接失败

```bash
# 1. 检查PostgreSQL状态
sudo systemctl status postgresql

# 2. 检查连接数
psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 3. 检查pg_hba.conf
cat /etc/postgresql/14/main/pg_hba.conf | grep -v "^#" | grep -v "^$"

# 4. 测试连接
psql -U fai_user -h localhost -d fai_system

# 5. 重启数据库
sudo systemctl restart postgresql
```

#### Celery任务不执行

```bash
# 1. 检查Celery状态
celery -A fai_system inspect active

# 2. 检查Redis连接
redis-cli -a password ping

# 3. 查看Celery日志
tail -50 /var/log/fai_system/celery.log

# 4. 重启Celery
sudo supervisorctl restart fai_celery
```

#### 文件上传失败

```bash
# 1. 检查Nginx配置
grep client_max_body_size /etc/nginx/sites-available/fai_system

# 2. 检查临时目录权限
ls -la /var/www/fai_system/media/

# 3. 检查磁盘空间
df -h

# 4. 检查S3存储配置
python manage.py shell
>>> from django.core.files.storage import default_storage
>>> default_storage.exists('test.txt')
```

### 7.2 性能问题排查

#### 响应慢

```bash
# 1. 检查慢查询日志
grep "duration:" /var/log/postgresql/*.log | tail -20

# 2. 分析慢查询
EXPLAIN ANALYZE <slow_query>;

# 3. 检查系统资源
top -c
iostat -x 1 5

# 4. 检查网络延迟
ping localhost
```

#### 内存泄漏

```bash
# 1. 监控进程内存
ps aux --sort=-%mem | head -10

# 2. 分析内存使用
python -c "
import tracemalloc
tracemalloc.start()
# 运行代码
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"

# 3. 重启worker释放内存
sudo supervisorctl restart fai_system
```

### 7.3 错误代码对照表

| 错误代码 | 含义 | 可能原因 | 解决方案 |
|----------|------|----------|----------|
| 500 | 服务器内部错误 | 代码异常 | 查看error.log |
| 502 | Bad Gateway | Gunicorn未运行 | 重启应用服务 |
| 503 | Service Unavailable | 服务过载 | 检查资源使用 |
| 504 | Gateway Timeout | 后端响应超时 | 增加超时时间 |
| ECONNREFUSED | 连接被拒绝 | 服务未启动 | 检查服务状态 |
| ETIMEDOUT | 连接超时 | 网络问题或服务过载 | 检查网络和负载 |

---

## 8. 应急响应

### 8.1 应急响应流程

```
1. 发现问题 → 2. 初步评估 → 3. 紧急处理 → 4. 根因分析 → 5. 永久修复
```

### 8.2 应急处理步骤

#### 服务宕机

```bash
# 1. 确认服务状态
sudo supervisorctl status
ss -tuln | grep 5000

# 2. 尝试重启服务
sudo supervisorctl restart all

# 3. 检查日志定位问题
tail -100 /var/log/fai_system/error.log

# 4. 如果无法启动，回滚到上一版本
cd /var/www/fai_system
git checkout HEAD~1
sudo supervisorctl restart fai_system
```

#### 数据库故障

```bash
# 1. 确认数据库状态
sudo systemctl status postgresql

# 2. 尝试重启
sudo systemctl restart postgresql

# 3. 如果无法启动，从备份恢复
# 参见 4.2 数据库恢复

# 4. 通知相关人员
echo "数据库故障，正在恢复..." | mail -s "紧急告警" admin@example.com
```

#### 数据丢失

```bash
# 1. 立即停止写入操作
sudo supervisorctl stop fai_system

# 2. 评估丢失范围
psql -U fai_user -d fai_system -c "SELECT COUNT(*) FROM parts;"

# 3. 从备份恢复
# 参见 4.2 数据库恢复

# 4. 验证数据完整性
python manage.py check
```

### 8.3 应急联系人

| 角色 | 姓名 | 电话 | 邮箱 |
|------|------|------|------|
| 系统管理员 | - | - | - |
| 数据库管理员 | - | - | - |
| 开发负责人 | - | - | - |
| 业务负责人 | - | - | - |

### 8.4 应急演练计划

- **演练频率**: 每季度一次
- **演练内容**: 
  - 数据库恢复演练
  - 服务故障切换演练
  - 数据备份恢复演练
- **演练记录**: 记录演练过程、发现的问题、改进措施

---

**文档版本历史**

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-03-13 | 初始版本 | FAI开发团队 |
