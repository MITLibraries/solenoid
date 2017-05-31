# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Record


class RecordAdmin(admin.ModelAdmin):
    list_filter = ('acq_method',)
    list_display = ('author', 'publisher_name', 'doi', 'is_sent')


admin.site.register(Record, RecordAdmin)
