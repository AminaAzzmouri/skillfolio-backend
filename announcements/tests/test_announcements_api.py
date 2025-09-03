"""
Integration tests for the Announcements API.

We keep these tests in the announcements app (do NOT mix with users/).
"""
# announcements/tests/test_announcements_api.py
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from announcements.models import Announcement, Fact


class AnnouncementsApiTests(APITestCase):
    def setUp(self):
        # If your endpoints require auth, authenticate a user:
        User = get_user_model()
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass12345"
        )
        self.client.force_authenticate(self.user)

        # Seed a couple of announcements
        self.a1 = Announcement.objects.create(
            title="ML Specialization — Feb intake",
            platform="Coursera",
            type="enrollment",
            url="https://example.com/ml",
            starts_at=date.today(),
            ends_at=date.today() + timedelta(days=10),
            tags=["AI", "Beginner"],
        )
        self.a2 = Announcement.objects.create(
            title="Modern JS Bootcamp — 40% OFF",
            platform="Udemy",
            type="discount",
            url="https://example.com/js",
            starts_at=date.today(),
            ends_at=date.today() + timedelta(days=5),
            discount_pct=40,
            price_original=79.99,
            price_current=47.99,
            tags=["JavaScript", "Web"],
        )

        Fact.objects.create(
            text="Sample fact",
            source="UnitTest Source",
            source_url="https://example.com",
            active=True,
        )

    def _items(self, response_data):
        # handle both paginated and non-paginated responses
        return response_data if isinstance(response_data, list) else response_data.get("results", [])

    def test_list_announcements(self):
        r = self.client.get("/api/announcements/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        items = self._items(r.data)
        self.assertGreaterEqual(len(items), 2)

    def test_filter_type_enrollment(self):
        r = self.client.get("/api/announcements/?type=enrollment")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        items = self._items(r.data)
        self.assertTrue(all(i["type"] == "enrollment" for i in items))

    def test_random_fact(self):
        r = self.client.get("/api/facts/random/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("text", r.data)
