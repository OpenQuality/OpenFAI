# Generated migration to add relation fields to FAIProject

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_faiproject_projectstep'),
        ('parts', '0001_initial'),
        ('inspections', '0001_initial'),
        ('measurements', '0001_initial'),
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='faiproject',
            name='part',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='parts.part',
                verbose_name='关联零件'
            ),
        ),
        migrations.AddField(
            model_name='faiproject',
            name='inspection_plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='inspections.inspectionplan',
                verbose_name='关联检验计划'
            ),
        ),
        migrations.AddField(
            model_name='faiproject',
            name='measurement_batch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='measurements.measurementbatch',
                verbose_name='关联测量批次'
            ),
        ),
        migrations.AddField(
            model_name='faiproject',
            name='inspection_report',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='reports.inspectionreport',
                verbose_name='关联检验报告'
            ),
        ),
    ]
