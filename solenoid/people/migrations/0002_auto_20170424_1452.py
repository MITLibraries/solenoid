# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dlc",
            name="liaison",
            field=models.ForeignKey(
                blank=True, null=True, to="people.Liaison", on_delete=models.CASCADE
            ),
        ),
    ]
