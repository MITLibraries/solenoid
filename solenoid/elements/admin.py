from django.contrib import admin

from .models import ElementsAPICall


class ReturnedListFilter(admin.SimpleListFilter):
    title = 'Response was returned'
    parameter_name = 'was_returned'

    def lookups(self, request, model_admin):
        return (
            ('true', 'true'),
            ('false', 'false'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(response_content__isnull=False)
        elif self.value() == 'false':
            return queryset.filter(response_content__isnull=True)
        else:
            return queryset


class RetryListFilter(admin.SimpleListFilter):
    title = 'Retry of other call'
    parameter_name = 'is_retry'

    def lookups(self, request, model_admin):
        return (
            ('true', 'true'),
            ('false', 'false'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(retry_of__isnull=False)
        elif self.value() == 'false':
            return queryset.filter(retry_of__isnull=True)
        else:
            return queryset


class ElementsAPICallAdmin(admin.ModelAdmin):
    list_filter = (ReturnedListFilter, RetryListFilter, 'response_status')
    list_display = ('response_status', 'retry_of', 'timestamp')


admin.site.register(ElementsAPICall, ElementsAPICallAdmin)
