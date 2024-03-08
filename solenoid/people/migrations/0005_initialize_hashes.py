# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib

from django.db import migrations


def initialize_hashes(apps, schema_editor):
    # We can't import the Author model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Author = apps.get_model("people", "Author")
    for author in Author.objects.all():
        # We can't use Author.get_hash because it doesn't deconstruct properly
        # to be available for migrations.
        author._mit_id_hash = hashlib.md5(author.mit_id.encode("utf-8")).hexdigest()
        author.save()


class Migration(migrations.Migration):

    dependencies = [
        ("people", "0004_auto_20170501_1559"),
    ]

    operations = [migrations.RunPython(initialize_hashes)]
