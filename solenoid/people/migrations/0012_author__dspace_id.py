# Generated by Django 2.2 on 2019-05-17 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0011_auto_20180308_1812'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='_dspace_id',
            field=models.CharField(default='', max_length=32),
            preserve_default=False,
        ),
    ]