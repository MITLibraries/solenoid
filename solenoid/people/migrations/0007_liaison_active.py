# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0006_remove_author_mit_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="liaison",
            name="active",
            field=models.BooleanField(default=True),
        ),
    ]
