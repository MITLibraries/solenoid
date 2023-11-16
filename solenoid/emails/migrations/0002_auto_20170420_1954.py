# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailmessage",
            name="original_text",
            field=models.TextField(editable=False),
        ),
    ]
