from django.contrib import admin

from .models import Liaison, DLC, Author


class DLCInline(admin.TabularInline):
    model = DLC
    fields = ("name",)


class LiaisonAdmin(admin.ModelAdmin):
    list_filter = ("active",)
    list_display = ("first_name", "last_name", "email_address", "active")
    inlines = (DLCInline,)


admin.site.register(Liaison, LiaisonAdmin)


class DLCAdmin(admin.ModelAdmin):
    list_filter = ("liaison",)
    list_display = ("name", "liaison")


admin.site.register(DLC, DLCAdmin)


class AuthorAdmin(admin.ModelAdmin):
    list_filter = ("dlc", "dlc__liaison")
    list_display = (
        "first_name",
        "last_name",
        "email",
        "dlc",
    )


admin.site.register(Author, AuthorAdmin)
