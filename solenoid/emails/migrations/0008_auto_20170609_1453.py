# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def initialize_authors(apps, schema_editor):
    EmailMessage = apps.get_model("emails", "EmailMessage")
    for email in EmailMessage.objects.all():
        email.author = email.record_set.first().author
        email.save()


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0007_emailmessage_author'),
    ]

    operations = [
    ]
