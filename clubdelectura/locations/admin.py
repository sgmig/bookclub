from django.contrib import admin

from locations.models import Location

# Register your models here.


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):

    list_display = ["name", "address"]
    search_fields = ["name", "address"]
    ordering = ["name"]
