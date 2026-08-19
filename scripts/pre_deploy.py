#!/usr/bin/env python3
"""
部署前脚本 - 更新数据库中的NULL值
在部署平台的数据库同步之前运行
"""

import os
import sys

# 添加项目根目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)

# 切换到项目目录
os.chdir(project_dir)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fai_system.settings')

import django
django.setup()

from django.db import connection

def update_null_values():
    """更新parts表中所有NULL值为默认值"""
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
    
    try:
        with connection.cursor() as cursor:
            for sql in updates:
                try:
                    cursor.execute(sql)
                    print(f"执行成功: {sql[:50]}...")
                except Exception as e:
                    print(f"执行失败 (可忽略): {sql[:50]}... - {e}")
        print("NULL值更新完成")
        return True
    except Exception as e:
        print(f"更新失败: {e}")
        return False

if __name__ == '__main__':
    update_null_values()
