from django.contrib import admin

from .models import EmailMessage


class EmailMessageAdmin(admin.ModelAdmin):
    readonly_fields = ("original_text",)


admin.site.register(EmailMessage, EmailMessageAdmin)
