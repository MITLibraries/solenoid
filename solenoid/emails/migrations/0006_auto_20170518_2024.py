# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0005_auto_20170517_1928"),
    ]

    operations = [
        migrations.RenameField(
            model_name="emailmessage",
            old_name="liaison",
            new_name="_liaison",
        ),
    ]
