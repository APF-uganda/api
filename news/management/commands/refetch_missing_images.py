"""
Management command: refetch_missing_images

Finds all news articles in Strapi that have no coverImage, deletes them,
then re-runs newsfetch so they get re-created with images.

Usage:
    # Dry run — just lists articles that would be deleted
    python manage.py refetch_missing_images --dry-run

    # Actually delete and re-fetch
    python manage.py refetch_missing_images
"""
import requests
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


STRAPI_BASE_URL = getattr(settings, "STRAPI_BASE_URL", "http://64.225.121.230:1337")
STRAPI_TOKEN = getattr(settings, "STRAPI_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {STRAPI_TOKEN}"}


def _fetch_all_articles_without_images():
    """
    Pages through Strapi and returns a list of articles where coverImage is null.
    Each item: {"id": ..., "documentId": ..., "title": ...}
    """
    articles = []
    page = 1
    page_size = 100

    while True:
        resp = requests.get(
            f"{STRAPI_BASE_URL}/api/news-articles",
            headers=HEADERS,
            params={
                "filters[coverImage][$null]": "true",
                "fields[0]": "title",
                "fields[1]": "documentId",
                "pagination[page]": page,
                "pagination[pageSize]": page_size,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("data", [])
        articles.extend(batch)

        meta = data.get("meta", {}).get("pagination", {})
        total_pages = meta.get("pageCount", 1)
        if page >= total_pages:
            break
        page += 1

    return articles


class Command(BaseCommand):
    help = "Delete Strapi news articles without a cover image, then re-fetch them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List articles that would be deleted without actually deleting them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.MIGRATE_HEADING("🔍 Fetching articles without cover images from Strapi..."))

        try:
            articles = _fetch_all_articles_without_images()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to query Strapi: {e}"))
            return

        if not articles:
            self.stdout.write(self.style.SUCCESS("✅ All articles already have cover images. Nothing to do."))
            return

        self.stdout.write(self.style.WARNING(f"Found {len(articles)} article(s) without a cover image:"))
        for article in articles:
            title = article.get("title") or article.get("attributes", {}).get("title", "(no title)")
            doc_id = article.get("documentId") or article.get("id")
            self.stdout.write(f"  • [{doc_id}] {title}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  Dry run — no articles were deleted. Remove --dry-run to proceed."))
            return

        # Delete each article
        self.stdout.write(self.style.MIGRATE_HEADING("\n🗑️  Deleting articles..."))
        deleted = 0
        failed = 0

        for article in articles:
            doc_id = article.get("documentId") or article.get("id")
            title = article.get("title") or article.get("attributes", {}).get("title", "(no title)")
            try:
                del_resp = requests.delete(
                    f"{STRAPI_BASE_URL}/api/news-articles/{doc_id}",
                    headers=HEADERS,
                    timeout=15,
                )
                if del_resp.status_code in [200, 204]:
                    self.stdout.write(self.style.SUCCESS(f"  🗑️  Deleted: {title[:60]}"))
                    deleted += 1
                else:
                    self.stdout.write(self.style.ERROR(f"  ❌ Failed to delete [{doc_id}]: {del_resp.text[:150]}"))
                    failed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error deleting [{doc_id}]: {e}"))
                failed += 1

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"\n📊 Deleted {deleted} article(s). Failed: {failed}.")
        )

        # Re-run newsfetch to pull them back in with images
        self.stdout.write(self.style.MIGRATE_HEADING("\n🔄 Re-fetching news from RSS feed..."))
        try:
            call_command("newsfetch")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ newsfetch failed: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("\n✅ Done. Articles re-fetched with images."))
