# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('dlc', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254, help_text='Author email address')),
                ('first_name', models.CharField(max_length=20)),
                ('last_name', models.CharField(max_length=40)),
                ('publisher_name', models.CharField(max_length=50)),
                ('acq_method', models.IntegerField(choices=[(0, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')])),
                ('citation', models.TextField()),
                ('status', models.CharField(max_length=7, default='Unsent', choices=[(0, 'Unsent'), (1, 'Sent'), (2, 'Invalid')])),
                ('status_timestamp', models.DateField(default=datetime.date.today)),
                ('paper_id', models.CharField(max_length=10, help_text='This is the Publication ID field from Elements; it is supposed to be unique but we will not be relying on it as a primary key here.')),
            ],
            options={
                'ordering': ['dlc', 'last_name'],
            },
        ),
    ]
