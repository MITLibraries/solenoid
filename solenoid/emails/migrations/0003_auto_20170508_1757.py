# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import ckeditor.fields


class Migration(migrations.Migration):
    dependencies = [
        ("emails", "0002_auto_20170420_1954"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailmessage",
            name="latest_text",
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="emailmessage",
            name="original_text",
            field=ckeditor.fields.RichTextField(editable=False),
        ),
    ]
