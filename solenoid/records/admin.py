# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Record


class RecordAdmin(admin.ModelAdmin):
    list_filter = ('acq_method',)
    list_display = ('doi', 'author', 'publisher_name', 'is_sent')


admin.site.register(Record, RecordAdmin)
