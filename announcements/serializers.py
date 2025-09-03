"""
announcements/serializers.py

DRF serializers that define the public JSON shapes returned to the frontend.
Keep these thin and explicit; they are our API contract.
"""
from rest_framework import serializers
from .models import Announcement, Fact


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "platform",
            "type",
            "url",
            "starts_at",
            "ends_at",
            "discount_pct",
            "price_original",
            "price_current",
            "tags",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_tags(self, value):
        # Always return a list; tolerate None/empty.
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("tags must be a list of strings")
        return value


class FactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fact
        fields = ["id", "text", "source", "source_url", "created_at"]
        read_only_fields = fields
