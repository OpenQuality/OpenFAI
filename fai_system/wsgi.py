"""
WSGI config for FAI System project.
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fai_system.settings')

# 在生产环境中自动初始化数据库
if os.environ.get('OPENFAI_ENV') == 'PROD':
    import django
    django.setup()
    
    from django.core.management import call_command
    from django.contrib.auth.models import User
    from django.db import OperationalError
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        print("[WSGI] 检查数据库状态...")
        
        # 运行迁移（使用 --fake-initial 处理已存在表的迁移）
        print("[WSGI] 运行数据库迁移...")
        try:
            call_command('migrate', '--fake-initial', verbosity=0)
            print("[WSGI] ✓ 数据库迁移完成")
        except Exception as migrate_err:
            err_str = str(migrate_err)
            if 'already exists' in err_str:
                # 表已存在但迁移未记录，尝试 fake 所有未应用迁移
                print(f"[WSGI] 检测到已存在表冲突，尝试标记迁移为已应用...")
                try:
                    call_command('migrate', '--fake', verbosity=0)
                    print("[WSGI] ✓ 迁移已标记为已应用")
                except Exception as fake_err:
                    print(f"[WSGI] 迁移标记失败: {fake_err}")
                    # 最后尝试普通迁移
                    call_command('migrate', verbosity=0)
                    print("[WSGI] ✓ 数据库迁移完成(重试)")
            else:
                raise
        
        # 创建管理员
        if not User.objects.filter(username='admin').exists():
            print("[WSGI] 创建管理员账号...")
            User.objects.create_superuser(
                username='admin',
                email='admin@fai-system.com',
                password='admin123',
                first_name='系统',
                last_name='管理员'
            )
            print("[WSGI] ✓ 管理员账号创建成功 (admin / admin123)")
        else:
            print("[WSGI] ✓ 管理员账号已存在")
        
        # 更新 parts 表中的 NULL 值（从 PartsConfig.ready() 迁移至此）
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # 修复 PostgreSQL 自增序列不同步问题
                # 原因：init_data.py 直接插入带显式id的数据，但序列未更新
                cursor.execute("""
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE column_default LIKE 'nextval%' 
                    AND table_schema = 'public';
                """)
                sequences = cursor.fetchall()
                for table_name, column_name in sequences:
                    try:
                        cursor.execute(
                            f"SELECT setval(pg_get_serial_sequence('{table_name}', '{column_name}'), "
                            f"COALESCE((SELECT MAX({column_name}) FROM {table_name}), 0) + 1, false);"
                        )
                    except Exception:
                        pass
                print("[WSGI] ✓ 自增序列已同步")
                
                # 修复 NOT NULL 约束与模型定义不一致的问题
                # 原因：生产环境 --fake 迁移跳过了 ALTER TABLE 操作
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'parts'
                    );
                """)
                if cursor.fetchone()[0]:
                    # cad_file_type: 模型定义 null=True，但数据库可能是 NOT NULL
                    alter_statements = [
                        "ALTER TABLE parts ALTER COLUMN cad_file_type DROP NOT NULL;",
                        "ALTER TABLE parts ALTER COLUMN model_3d_file_type DROP NOT NULL;",
                    ]
                    for sql in alter_statements:
                        try:
                            cursor.execute(sql)
                        except Exception:
                            pass  # 列已经是 nullable 或不存在
                    
                    updates = [
                        "UPDATE parts SET cad_file_original_name = '' WHERE cad_file_original_name IS NULL;",
                        "UPDATE parts SET drawing_file_original_name = '' WHERE drawing_file_original_name IS NULL;",
                        "UPDATE parts SET pdf_file_original_name = '' WHERE pdf_file_original_name IS NULL;",
                        "UPDATE parts SET model_3d_file_original_name = '' WHERE model_3d_file_original_name IS NULL;",
                        "UPDATE parts SET model_3d_file_type = '' WHERE model_3d_file_type IS NULL;",
                        "UPDATE parts SET cad_file_size = 0 WHERE cad_file_size IS NULL;",
                        "UPDATE parts SET drawing_file_size = 0 WHERE drawing_file_size IS NULL;",
                        "UPDATE parts SET pdf_file_size = 0 WHERE pdf_file_size IS NULL;",
                        "UPDATE parts SET model_3d_file_size = 0 WHERE model_3d_file_size IS NULL;",
                    ]
                    for sql in updates:
                        try:
                            cursor.execute(sql)
                        except Exception:
                            pass
                    print("[WSGI] ✓ 零件数据NULL值已更新")
        except Exception:
            pass
            
        print("[WSGI] 数据库初始化完成！")
    except Exception as e:
        print(f"[WSGI] 数据库初始化警告: {e}")
        # 不中断启动，允许应用继续运行

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
