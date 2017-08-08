# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0009_auto_20170609_1455'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailmessage',
            name='new_citations',
            field=models.BooleanField(default=False),
        ),
    ]
