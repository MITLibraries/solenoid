# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0003_auto_20170508_1757"),
        ("records", "0004_record_paper_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="record",
            name="email",
            field=models.ForeignKey(
                blank=True, null=True, to="emails.EmailMessage", on_delete=models.CASCADE
            ),
        ),
    ]
