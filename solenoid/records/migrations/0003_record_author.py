# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
        ('records', '0002_auto_20170419_1825'),
    ]

    operations = [
        migrations.AddField(
            model_name='record',
            name='author',
            field=models.ForeignKey(default=0, to='people.Author'),
            preserve_default=False,
        ),
    ]
