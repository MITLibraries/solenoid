# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Author",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, help_text="Author email address"),
                ),
                ("first_name", models.CharField(max_length=20)),
                ("last_name", models.CharField(max_length=40)),
                ("mit_id", models.CharField(max_length=10)),
            ],
            options={
                "verbose_name_plural": "Authors",
                "verbose_name": "Author",
            },
        ),
        migrations.CreateModel(
            name="DLC",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name_plural": "DLCs",
                "verbose_name": "DLC",
            },
        ),
        migrations.CreateModel(
            name="Liaison",
            fields=[
                (
                    "id",
                    models.AutoField(
                        serialize=False,
                        verbose_name="ID",
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("first_name", models.CharField(max_length=15)),
                ("last_name", models.CharField(max_length=30)),
                ("email_address", models.EmailField(max_length=254)),
            ],
            options={
                "verbose_name_plural": "Liaisons",
                "verbose_name": "Liaison",
            },
        ),
        migrations.AddField(
            model_name="dlc",
            name="liaison",
            field=models.ForeignKey(to="people.Liaison", on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name="author",
            name="dlc",
            field=models.ForeignKey(to="people.DLC", on_delete=models.CASCADE),
        ),
    ]
