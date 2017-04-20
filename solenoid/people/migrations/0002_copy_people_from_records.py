# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def copy_people_data(apps, schema_editor):
    """Create author objects corresponding to all the different Authors
    referenced in Records. Link records to the appropriate Author. This
    migrates data from Record to Author, allowing us to delete Author-related
    fields from Record in a subsequent migration.
    """
    Record = apps.get_model('records', 'Record')
    Author = apps.get_model('people', 'Author')

    for record in Record.objects.all():
        # Email almost certainly uniquely identifies the author, so we'll check
        # that to see whether we've already created an Author object for this
        # record.
        try:
            author = Author.objects.get(email=record.email)
        # We cannot catch Author.DoesNotExist, because the migrations
        # infrastructure actually throws a different error.
        except:
            author = Author.objects.create(
                dlc=record.dlc,
                email=record.email,
                first_name=record.first_name,
                last_name=record.last_name 
            )
        record.author = author
        record.save()



class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
        ('records', '0003_record_author'),
    ]

    operations = [
        migrations.RunPython(copy_people_data)
    ]
