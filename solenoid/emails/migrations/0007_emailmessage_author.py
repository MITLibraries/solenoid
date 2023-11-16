# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0009_auto_20170522_1621"),
        ("emails", "0006_auto_20170518_2024"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailmessage",
            name="author",
            field=models.ForeignKey(
                blank=True, null=True, to="people.Author", on_delete=models.CASCADE
            ),
        ),
    ]
