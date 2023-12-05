# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0002_auto_20170424_1452"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dlc",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
