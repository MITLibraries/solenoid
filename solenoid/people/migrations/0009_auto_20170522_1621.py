# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0008_auto_20170522_1620"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="author",
            options={
                "verbose_name": "Author",
                "verbose_name_plural": "Authors",
                "ordering": ["last_name", "first_name"],
            },
        ),
        migrations.AlterModelOptions(
            name="dlc",
            options={
                "verbose_name": "DLC",
                "verbose_name_plural": "DLCs",
                "ordering": ["name"],
            },
        ),
    ]
