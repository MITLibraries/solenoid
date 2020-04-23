# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0008_auto_20170609_1453'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailmessage',
            name='author',
            field=models.ForeignKey(to='people.Author',
                                    on_delete=models.CASCADE),
        ),
    ]
