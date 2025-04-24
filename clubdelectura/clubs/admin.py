from django.contrib import admin
from clubs.models import Club, ClubMembership

# Register your models here.


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "is_admin", "joined_at")
    search_fields = ("user", "club")
    list_filter = ("is_admin",)


class ClubMembershipInline(admin.TabularInline):
    model = ClubMembership
    extra = 1


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name", "created_by")
    inlines = [ClubMembershipInline]
