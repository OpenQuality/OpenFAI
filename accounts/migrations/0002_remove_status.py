# 删除 status 列的迁移
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]
    
    operations = [
        # 这个迁移文件是一个占位符
        # 实际的数据库修复需要在部署系统外部完成
        # 此文件用于标记迁移链完整
    ]
