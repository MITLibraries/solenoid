# Generated by Django 3.2.5 on 2021-07-16 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0015_auto_20200403_1856"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="acq_method",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="record",
            name="doi",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="record",
            name="paper_id",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="record",
            name="publisher_name",
            field=models.CharField(max_length=255),
        ),
    ]
