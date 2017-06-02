# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0007_auto_20170526_1825'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='record',
            unique_together=set([('author', 'paper_id')]),
        ),
    ]
