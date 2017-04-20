# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='record',
            name='paper_id',
        ),
        migrations.AddField(
            model_name='record',
            name='doi',
            field=models.CharField(default=0, max_length=30),
            preserve_default=False,
        ),
    ]
