from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0001_initial'),
    ]

    operations = [
        # 重命名字段
        migrations.RenameField(
            model_name='measurementbatch',
            old_name='temperature',
            new_name='environment_temp',
        ),
        migrations.RenameField(
            model_name='measurementbatch',
            old_name='humidity',
            new_name='environment_humidity',
        ),
        # 修改字段属性
        migrations.AlterField(
            model_name='measurementbatch',
            name='equipment_type',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='设备类型'),
        ),
        migrations.AlterField(
            model_name='measurementbatch',
            name='equipment_id',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='设备编号'),
        ),
        migrations.AlterField(
            model_name='measurementbatch',
            name='measured_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='测量时间'),
        ),
        migrations.AlterField(
            model_name='measurementbatch',
            name='measured_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
                verbose_name='测量人员',
            ),
        ),
        migrations.AlterField(
            model_name='measurementbatch',
            name='status',
            field=models.CharField(
                choices=[('DRAFT', '草稿'), ('IN_PROGRESS', '测量中'), ('COMPLETED', '已完成'), ('REVIEWED', '已审核'), ('APPROVED', '已批准')],
                default='DRAFT',
                max_length=20,
                verbose_name='状态',
            ),
        ),
    ]
