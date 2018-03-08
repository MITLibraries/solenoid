# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0004_remove_emailmessage_author'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailmessage',
            name='liaison',
            field=models.ForeignKey(blank=True, null=True, to='people.Liaison', on_delete=models.CASCADE),
        ),
    ]
