# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0007_liaison_active'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='liaison',
            options={'verbose_name': 'Liaison',
                     'verbose_name_plural': 'Liaisons',
                     'ordering': ['last_name', 'first_name']},
        ),
    ]
