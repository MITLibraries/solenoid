# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Email',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('original_text', models.TextField()),
                ('latest_text', models.TextField(blank=True, null=True)),
                ('date_sent', models.DateField(blank=True, null=True)),
                ('to_email', models.EmailField(max_length=254)),
            ],
            options={
                'verbose_name_plural': 'Emails',
                'verbose_name': 'Email',
            },
        ),
    ]
