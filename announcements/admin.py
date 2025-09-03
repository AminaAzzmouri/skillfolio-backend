"""
announcements/admin.py

Minimal admin to allow quick manual curation and CSV import via copy/paste.
"""
from django.contrib import admin
from .models import Announcement, Fact


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "platform", "type", "starts_at", "ends_at", "discount_pct", "created_at")
    list_filter = ("platform", "type", "starts_at", "ends_at")
    search_fields = ("title", "platform", "url", "tags")
    ordering = ("-starts_at", "-created_at")


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("short", "source", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("text", "source", "source_url")

    def short(self, obj):
        return (obj.text or "")[:80]