import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from announcements.models import Announcement

class Command(BaseCommand):
    help = "Seed Announcement rows from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to announcements JSON")

    def handle(self, *args, **opts):
        path = Path(opts["json_path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("results", [])
        created = 0
        for x in items:
            obj, made = Announcement.objects.get_or_create(
                title=x.get("title", ""),
                platform=x.get("platform", ""),
                defaults=dict(
                    type=x.get("type", "enrollment"),
                    url=x.get("url", ""),
                    starts_at=x.get("starts_at") or None,
                    ends_at=x.get("ends_at") or None,
                    discount_pct=x.get("discount_pct"),
                    price_original=x.get("price_original"),
                    price_current=x.get("price_current"),
                    tags=x.get("tags", []) or [],
                ),
            )
            created += 1 if made else 0
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} announcement(s)."))
