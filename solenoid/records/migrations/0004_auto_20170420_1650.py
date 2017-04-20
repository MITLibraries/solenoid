# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0003_record_author'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='record',
            options={'ordering': ['author__dlc', 'author__last_name']},
        ),
        migrations.RemoveField(
            model_name='record',
            name='dlc',
        ),
        migrations.RemoveField(
            model_name='record',
            name='email',
        ),
        migrations.RemoveField(
            model_name='record',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='record',
            name='last_name',
        ),
    ]
