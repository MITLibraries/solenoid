# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ElementsAPICall',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('request_data', models.TextField(help_text='The xml sent (i.e. the "data"kwarg in the requests.patch() call.')),
                ('request_url', models.URLField(help_text='The URL to which the call was sent (i.e. the "url" argument to requests.patch()).')),
                ('response_content', models.TextField(blank=True, null=True, help_text='The content of the response. Will be blank if there was noresponse (i.e. due to timeout or other failed call).')),
                ('response_status', models.CharField(max_length=3, blank=True, null=True, help_text='The HTTP status code of the response. Will be blank ifthere was no response.')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('retry_of', models.ForeignKey(blank=True, null=True, on_delete=models.CASCADE, help_text='If this call is a retry of a previous failed call, this isa ForeignKey to that call. Otherwise it is blank.', to='elements.ElementsAPICall')),
            ],
        ),
    ]
