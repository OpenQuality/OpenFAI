# -*- coding: utf-8 -*-
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('workflows', '0002_nonconformancereport_nonconformanceaction'),
        ('parts', '__first__'),
    ]

    operations = [
        migrations.AddField(
            model_name='nonconformancereport',
            name='part',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='non_conformances',
                to='parts.part',
                verbose_name='零件'
            ),
        ),
    ]
