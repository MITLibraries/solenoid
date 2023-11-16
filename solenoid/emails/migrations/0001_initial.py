# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailMessage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        primary_key=True,
                        auto_created=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("original_text", models.TextField()),
                ("latest_text", models.TextField(blank=True, null=True)),
                ("date_sent", models.DateField(blank=True, null=True)),
                (
                    "author",
                    models.ForeignKey(to="people.Author", on_delete=models.CASCADE),
                ),
                (
                    "liaison",
                    models.ForeignKey(to="people.Liaison", on_delete=models.CASCADE),
                ),
            ],
            options={
                "verbose_name_plural": "Emails",
                "verbose_name": "Email",
            },
        ),
    ]
