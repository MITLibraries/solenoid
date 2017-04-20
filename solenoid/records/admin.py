from django.contrib import admin

from .models import Record


class RecordAdmin(admin.ModelAdmin):
    list_filter = ('status', 'acq_method')
    list_display = ('doi', 'author', 'publisher_name', 'status')


admin.site.register(Record, RecordAdmin)
