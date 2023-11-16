# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0003_auto_20170426_2005"),
    ]

    operations = [
        migrations.AddField(
            model_name="author",
            name="_mit_id_hash",
            field=models.CharField(
                max_length=32,
                default=0,
                help_text="This "
                "stores the *hash* of the MIT ID, not the "
                "MIT ID itself. We want to have a unique "
                "identifier for the author but we don't "
                "want to be storing sensitive data "
                "offsite. Hashing the ID achieves "
                "our goals.",
            ),
            preserve_default=False,
        ),
    ]
