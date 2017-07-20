# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('publisher_name', models.CharField(max_length=50)),
                ('acq_method', models.CharField(choices=[('RECRUIT_FROM_AUTHOR_MANUSCRIPT', 'RECRUIT_FROM_AUTHOR_MANUSCRIPT'), ('RECRUIT_FROM_AUTHOR_FPV', 'RECRUIT_FROM_AUTHOR_FPV')], max_length=32)),
                ('citation', models.TextField()),
                ('status', models.CharField(choices=[('Unsent', 'Unsent'), ('Sent', 'Sent'), ('Invalid', 'Invalid')], default='Unsent', max_length=7)),
                ('status_timestamp', models.DateField(default=datetime.date.today)),
                ('paper_id', models.CharField(help_text='This is the Publication ID field from Elements; it is supposed to be unique but we will not be relying on it as a primary key here.', max_length=10)),
                ('author', models.ForeignKey(to='people.Author')),
            ],
            options={
                'ordering': ['author__dlc', 'author__last_name'],
            },
        ),
    ]
