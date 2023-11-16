# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("records", "0010_auto_20170802_1425"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="publisher_name",
            field=models.CharField(max_length=75),
        ),
    ]
