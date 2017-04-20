from django.contrib import admin

from .models import Record


class RecordAdmin(admin.ModelAdmin):
    list_filter = ('status', 'acq_method')
    list_display = ('paper_id', 'author', 'publisher_name', 'status')


admin.site.register(Record, RecordAdmin)
