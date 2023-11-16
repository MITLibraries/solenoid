# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0009_auto_20170522_1621"),
    ]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="first_name",
            field=models.CharField(max_length=30),
        ),
    ]
