# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0009_auto_20170602_1731"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="source",
            field=models.CharField(max_length=25),
        ),
    ]
