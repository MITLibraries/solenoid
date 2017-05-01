# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0005_initialize_hashes'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='author',
            name='mit_id',
        ),
    ]
