# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0008_auto_20170602_1425"),
    ]

    operations = [
        migrations.AddField(
            model_name="record",
            name="elements_id",
            field=models.CharField(max_length=50, default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="record",
            name="source",
            field=models.CharField(max_length=15, default="Manual"),
            preserve_default=False,
        ),
    ]
