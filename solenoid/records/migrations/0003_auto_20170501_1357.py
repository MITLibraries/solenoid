# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("records", "0002_auto_20170420_2027"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="doi",
            field=models.CharField(max_length=30, blank=True),
        ),
    ]
