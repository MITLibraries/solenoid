# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0005_record_email"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="record",
            name="status",
        ),
        migrations.RemoveField(
            model_name="record",
            name="status_timestamp",
        ),
    ]
