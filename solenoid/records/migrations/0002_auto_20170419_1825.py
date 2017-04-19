# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='record',
            name='acq_method',
            field=models.CharField(max_length=32, choices=[('RECRUIT_FROM_AUTHOR_MANUSCRIPT', 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'), ('RECRUIT_FROM_AUTHOR_FPV_ACCEPTED', 'RECRUIT_FROM_AUTHOR_FPV_ACCEPTED')]),
        ),
        migrations.AlterField(
            model_name='record',
            name='status',
            field=models.CharField(max_length=7, default='Unsent', choices=[('Unsent', 'Unsent'), ('Sent', 'Sent'), ('Invalid', 'Invalid')]),
        ),
    ]
