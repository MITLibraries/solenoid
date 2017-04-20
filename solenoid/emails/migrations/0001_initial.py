# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0002_copy_people_from_records'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('original_text', models.TextField()),
                ('latest_text', models.TextField(null=True, blank=True)),
                ('date_sent', models.DateField(null=True, blank=True)),
                ('author', models.ForeignKey(to='people.Author')),
            ],
            options={
                'verbose_name_plural': 'Emails',
                'verbose_name': 'Email',
            },
        ),
    ]
