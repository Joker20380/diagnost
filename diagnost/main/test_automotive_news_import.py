import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import (
    TestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone

from main.models import (
    CategoryNews,
    News,
)


@override_settings(
    ALLOWED_HOSTS=[
        "testserver",
    ],
    EMAIL_BACKEND=(
        "django.core.mail.backends."
        "locmem.EmailBackend"
    ),
)
class AutomotiveNewsImportTests(TestCase):
    def setUp(self):
        manual_category = (
            CategoryNews.objects.create(
                name="Ручные новости",
                slug="manual-news",
            )
        )

        self.manual_news = News.objects.create(
            title="Ручная новость",
            slug="manual-news-item",
            content="<p>Ручной материал</p>",
            time_create=timezone.now(),
            is_published=True,
            cat=manual_category,
        )

    def make_feed(
        self,
        title="Первая автоновость",
    ):
        return {
            "source": (
                "clearfield_generated_"
                "automotive_news"
            ),
            "created_at": (
                timezone.now().isoformat()
            ),
            "items": [
                {
                    "source_id": "auto-101",
                    "title": title,
                    "slug": (
                        "diagnostika-podveski-"
                        "vo-vladikavkaze"
                    ),
                    "meta_description": (
                        "Как вовремя обнаружить "
                        "неисправности подвески."
                    ),
                    "body": (
                        "## Диагностика подвески\n\n"
                        "Проверьте автомобиль при "
                        "появлении стука.\n\n"
                        "- Осмотр деталей\n"
                        "- Проверка люфтов\n\n"
                        "<script>alert(1)</script>"
                    ),
                    "source_note": (
                        "Материал подготовлен по "
                        "открытым источникам."
                    ),
                    "source_urls": [
                        (
                            "https://example.com/"
                            "auto/101"
                        ),
                    ],
                    "image_topic": "suspension",
                    "created_at": (
                        timezone.now().isoformat()
                    ),
                }
            ],
        }

    def run_import(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feed.json"

            path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            call_command(
                (
                    "import_generated_"
                    "automotive_news"
                ),
                str(path),
                verbosity=0,
            )

    def test_import_is_idempotent_and_hidden(self):
        self.run_import(
            self.make_feed()
        )

        source_id = (
            "clearfield_generated_"
            "automotive_news:auto-101"
        )

        imported = News.objects.get(
            generated_source_id=source_id
        )

        self.assertFalse(
            imported.is_published
        )

        self.assertIn(
            "<h2>Диагностика подвески</h2>",
            imported.content,
        )

        self.assertIn(
            (
                "&lt;script&gt;alert(1)"
                "&lt;/script&gt;"
            ),
            imported.content,
        )

        self.assertEqual(
            imported.source_urls,
            [
                (
                    "https://example.com/"
                    "auto/101"
                ),
            ],
        )

        self.assertEqual(
            self.client.get(
                imported.get_absolute_url(),
                secure=True,
            ).status_code,
            404,
        )

        blog_response = self.client.get(
            reverse("blog"),
            secure=True,
        )

        self.assertNotContains(
            blog_response,
            imported.title,
        )

        self.run_import(
            self.make_feed(
                title=(
                    "Обновлённая автоновость"
                ),
            )
        )

        self.assertEqual(
            News.objects.filter(
                generated_source_id=source_id,
            ).count(),
            1,
        )

        imported.refresh_from_db()

        self.assertEqual(
            imported.title,
            "Обновлённая автоновость",
        )

        self.assertFalse(
            imported.is_published
        )

        self.assertTrue(
            News.objects.filter(
                pk=self.manual_news.pk,
                title="Ручная новость",
                is_published=True,
            ).exists()
        )

        News.objects.filter(
            pk=imported.pk,
        ).update(
            is_published=True,
        )

        imported.refresh_from_db()

        self.assertEqual(
            self.client.get(
                imported.get_absolute_url(),
                secure=True,
            ).status_code,
            200,
        )

        published_blog = self.client.get(
            reverse("blog"),
            secure=True,
        )

        self.assertContains(
            published_blog,
            imported.title,
        )
