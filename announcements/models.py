"""
announcements/models.py

Data model for:
- Announcement: course enrollments & discounts from platforms (Coursera, Udemy, 365, etc.)
- Fact: short motivational factoids for the Home page

Notes & design choices
----------------------
- "type" is constrained to 'enrollment' or 'discount' via TextChoices.
- Monetary fields use Decimal (not float) to avoid rounding issues.
- tags is a JSONField (list of strings) for simple faceting/searching later.
- Lightweight indexing on platform/type/dates for common queries.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Announcement(models.Model):
    class Type(models.TextChoices):
        ENROLLMENT = "enrollment", "Enrollment"
        DISCOUNT = "discount", "Discount"

    title = models.CharField(max_length=200, help_text="Human title shown to users.")
    platform = models.CharField(max_length=80, db_index=True, help_text="e.g. Udemy, Coursera, 365 Data Science")
    type = models.CharField(max_length=12, choices=Type.choices, db_index=True)
    url = models.URLField(max_length=500, help_text="External page to visit/enroll.")
    starts_at = models.DateField(null=True, blank=True, db_index=True)
    ends_at = models.DateField(null=True, blank=True, db_index=True)

    # Discount-specific extras (nullable for 'enrollment' rows)
    discount_pct = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0–100; only used when type=discount."
    )
    price_original = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    price_current = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)

    tags = models.JSONField(default=list, blank=True, help_text="List of strings, e.g. ['AI','Beginner']")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-starts_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.platform}: {self.title}"


class Fact(models.Model):
    """
    Short, sourceable fact used by the 'Did you know?' card.
    """
    text = models.TextField(help_text="The fact body shown on the Home page.")
    source = models.CharField(max_length=200, blank=True, help_text="Short label for the source (optional).")
    source_url = models.URLField(max_length=500, blank=True, help_text="Clickable URL for the source (optional).")
    active = models.BooleanField(default=True, help_text="If false, excluded from the random picker.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (self.text or "")[:60] + ("…" if len(self.text or "") > 60 else "")
