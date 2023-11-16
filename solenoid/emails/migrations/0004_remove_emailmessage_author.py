# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0003_auto_20170508_1757"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="emailmessage",
            name="author",
        ),
    ]
