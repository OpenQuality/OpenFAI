# Generated manually to fix production database
# 支持 SQLite 和 PostgreSQL

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # 禁用事务以避免 PostgreSQL 限制

    dependencies = [
        ('parts', '0002_part_batch_serial_number_part_department_and_more'),
    ]

    operations = [
        # 第一步：更新 NULL 值为默认值
        migrations.RunSQL(
            sql="""
                UPDATE parts SET fai_quantity = 1 WHERE fai_quantity IS NULL;
                UPDATE parts SET production_quantity = 0 WHERE production_quantity IS NULL;
            """,
            reverse_sql="""
                -- 回滚不需要操作
            """,
        ),
        # 第二步：设置字段约束（使用 Django 操作保证兼容性）
        migrations.AlterField(
            model_name='part',
            name='fai_quantity',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='part',
            name='production_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
