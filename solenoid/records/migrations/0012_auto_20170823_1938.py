# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0011_auto_20170811_1433"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="doi",
            field=models.CharField(max_length=45, blank=True),
        ),
    ]
