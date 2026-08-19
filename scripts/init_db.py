#!/usr/bin/env python
"""
数据库初始化脚本
在生产环境中自动运行迁移和创建管理员账号
"""
import os
import sys
import django

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fai_system.settings')

django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from django.db import OperationalError
import logging

logger = logging.getLogger(__name__)


def run_migrations():
    """运行数据库迁移"""
    try:
        print("正在运行数据库迁移...")
        call_command('migrate', verbosity=0)
        print("✓ 数据库迁移完成")
        return True
    except OperationalError as e:
        print(f"✗ 数据库迁移失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 数据库迁移出错: {e}")
        return False


def create_superuser():
    """创建管理员账号"""
    try:
        # 检查admin用户是否已存在
        if User.objects.filter(username='admin').exists():
            print("✓ 管理员账号已存在")
            return True
        
        # 创建管理员账号
        User.objects.create_superuser(
            username='admin',
            email='admin@fai-system.com',
            password='admin123',
            first_name='系统',
            last_name='管理员'
        )
        print("✓ 管理员账号创建成功 (admin / admin123)")
        return True
    except Exception as e:
        print(f"✗ 创建管理员账号失败: {e}")
        return False


def init_database():
    """初始化数据库"""
    print("=" * 50)
    print("开始初始化数据库...")
    print("=" * 50)
    
    # 运行迁移
    if not run_migrations():
        return False
    
    # 创建管理员
    if not create_superuser():
        return False
    
    print("=" * 50)
    print("数据库初始化完成！")
    print("=" * 50)
    return True


if __name__ == '__main__':
    init_database()
