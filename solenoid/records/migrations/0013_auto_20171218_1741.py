# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0012_auto_20170823_1938'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='record',
            name='elements_id',
        ),
        migrations.RemoveField(
            model_name='record',
            name='source',
        ),
        migrations.AlterField(
            model_name='record',
            name='acq_method',
            field=models.CharField(max_length=32, blank=True,
                                   choices=[('RECRUIT_FROM_AUTHOR_MANUSCRIPT',
                                             'RECRUIT_FROM_AUTHOR_MANUSCRIPT'),
                                            ('RECRUIT_FROM_AUTHOR_FPV',
                                             'RECRUIT_FROM_AUTHOR_FPV'),
                                            ('', ''),
                                            ('INDIVIDUAL_DOWNLOAD',
                                             'INDIVIDUAL_DOWNLOAD')]),
        ),
    ]
