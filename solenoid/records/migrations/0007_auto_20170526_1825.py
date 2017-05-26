# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0006_auto_20170524_1851'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('text', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='record',
            name='message',
            field=models.ForeignKey(blank=True, null=True, to='records.Message'),
        ),
    ]
