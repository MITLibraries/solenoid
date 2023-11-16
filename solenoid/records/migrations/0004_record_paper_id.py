# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("records", "0003_auto_20170501_1357"),
    ]

    operations = [
        migrations.AddField(
            model_name="record",
            name="paper_id",
            field=models.CharField(max_length=10, default=0),
            preserve_default=False,
        ),
    ]
