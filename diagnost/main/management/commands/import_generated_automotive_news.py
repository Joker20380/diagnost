import hashlib
import html
import json
import re
from datetime import datetime, time
from pathlib import Path
from urllib.parse import urlsplit

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import (
    parse_date,
    parse_datetime,
)
from django.utils.html import escape
from django.utils.text import slugify

from main.models import (
    CategoryNews,
    News,
)


EXPECTED_SOURCE = (
    "clearfield_generated_automotive_news"
)


def compact(value, limit=None):
    text = re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()

    if limit is not None:
        return text[:limit]

    return text


def parse_timestamp(value):
    raw = compact(value)

    if not raw:
        return timezone.now()

    parsed = parse_datetime(raw)

    if parsed is None:
        parsed_date = parse_date(raw)

        if parsed_date is not None:
            parsed = datetime.combine(
                parsed_date,
                time.min,
            )

    if parsed is None:
        raise CommandError(
            f"Invalid datetime: {raw}"
        )

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)

    return parsed


def normalize_source_urls(value):
    if not value:
        return []

    if isinstance(value, str):
        candidates = re.split(
            r"[\r\n,]+",
            value,
        )
    elif isinstance(value, list):
        candidates = value
    else:
        raise CommandError(
            "source_urls must be a list or string"
        )

    result = []
    seen = set()

    for candidate in candidates:
        url = compact(candidate)

        if not url:
            continue

        parsed = urlsplit(url)

        if (
            parsed.scheme not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            raise CommandError(
                f"Invalid source URL: {url}"
            )

        if url in seen:
            continue

        seen.add(url)
        result.append(url)

    return result[:20]


def clean_meta_description(value, fallback):
    text = compact(
        value or fallback
    )

    text = html.unescape(text)
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )
    text = re.sub(
        r"(?m)^\s{0,3}#{1,6}\s*",
        "",
        text,
    )
    text = text.replace("**", "")
    text = compact(text)

    return text[:320]


def render_plain_markdown(value):
    """
    Преобразует ограниченный Markdown в безопасный HTML.

    Поддерживаются заголовки, абзацы и списки.
    Любой входной HTML экранируется.
    """

    raw = str(value or "").strip()

    if not raw:
        raise CommandError(
            "News body is empty"
        )

    result = []
    paragraph = []
    list_type = None
    list_items = []

    def flush_paragraph():
        nonlocal paragraph

        if not paragraph:
            return

        content = " ".join(
            compact(line)
            for line in paragraph
            if compact(line)
        )

        if content:
            result.append(
                f"<p>{escape(content)}</p>"
            )

        paragraph = []

    def flush_list():
        nonlocal list_type, list_items

        if not list_type or not list_items:
            list_type = None
            list_items = []
            return

        items_html = "".join(
            f"<li>{escape(item)}</li>"
            for item in list_items
        )

        result.append(
            f"<{list_type}>"
            f"{items_html}"
            f"</{list_type}>"
        )

        list_type = None
        list_items = []

    for original_line in raw.splitlines():
        line = original_line.strip()

        if not line:
            flush_paragraph()
            flush_list()
            continue

        heading = re.match(
            r"^(#{1,4})\s+(.+)$",
            line,
        )

        if heading:
            flush_paragraph()
            flush_list()

            level = len(
                heading.group(1)
            )

            result.append(
                f"<h{level}>"
                f"{escape(compact(heading.group(2)))}"
                f"</h{level}>"
            )
            continue

        unordered = re.match(
            r"^[-*]\s+(.+)$",
            line,
        )

        if unordered:
            flush_paragraph()

            if list_type not in {
                None,
                "ul",
            }:
                flush_list()

            list_type = "ul"
            list_items.append(
                compact(unordered.group(1))
            )
            continue

        ordered = re.match(
            r"^\d+[.)]\s+(.+)$",
            line,
        )

        if ordered:
            flush_paragraph()

            if list_type not in {
                None,
                "ol",
            }:
                flush_list()

            list_type = "ol"
            list_items.append(
                compact(ordered.group(1))
            )
            continue

        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()

    return "\n".join(result)


def unique_slug(raw_slug, title, source_key):
    base = slugify(
        compact(raw_slug or title)
    )

    if not base:
        digest = hashlib.sha1(
            source_key.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()[:10]

        base = f"automotive-news-{digest}"

    base = base[:255]

    if not News.objects.filter(
        slug=base,
    ).exists():
        return base

    digest = hashlib.sha1(
        source_key.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()[:8]

    counter = 1

    while True:
        counter_suffix = (
            ""
            if counter == 1
            else f"-{counter}"
        )

        suffix = (
            f"-{digest}"
            f"{counter_suffix}"
        )

        candidate = (
            base[: 255 - len(suffix)]
            + suffix
        )

        if not News.objects.filter(
            slug=candidate,
        ).exists():
            return candidate

        counter += 1


class Command(BaseCommand):
    help = (
        "Import a Clearfield automotive news "
        "JSON feed into main.News."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "feed_path",
            type=str,
        )
        parser.add_argument(
            "--category-name",
            default="Автомобильные новости",
        )
        parser.add_argument(
            "--category-slug",
            default="automotive-news",
        )
        parser.add_argument(
            "--expected-source",
            default=EXPECTED_SOURCE,
        )
        parser.add_argument(
            "--publish",
            action="store_true",
            help=(
                "Publish new imported items. "
                "Without this flag they remain drafts."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
        )

    def handle(self, *args, **options):
        feed_path = Path(
            options["feed_path"]
        ).expanduser()

        if not feed_path.is_file():
            raise CommandError(
                f"Feed not found: {feed_path}"
            )

        if (
            options["dry_run"]
            and options["publish"]
        ):
            raise CommandError(
                "--dry-run and --publish "
                "cannot be used together"
            )

        try:
            payload = json.loads(
                feed_path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise CommandError(
                f"Cannot read feed: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise CommandError(
                "Feed root must be an object"
            )

        source = compact(
            payload.get("source")
        )

        expected_source = compact(
            options["expected_source"]
        )

        if source != expected_source:
            raise CommandError(
                "Unexpected feed source: "
                f"{source!r}; expected "
                f"{expected_source!r}"
            )

        items = payload.get("items")

        if not isinstance(items, list):
            raise CommandError(
                "Feed items must be a list"
            )

        counters = {
            "created": 0,
            "updated": 0,
            "unchanged": 0,
        }

        with transaction.atomic():
            category, _ = (
                CategoryNews.objects.get_or_create(
                    slug=options[
                        "category_slug"
                    ],
                    defaults={
                        "name": options[
                            "category_name"
                        ],
                    },
                )
            )

            for position, item in enumerate(
                items,
                start=1,
            ):
                if not isinstance(item, dict):
                    raise CommandError(
                        f"Item #{position} "
                        "must be an object"
                    )

                external_id = compact(
                    item.get("source_id")
                    or item.get("external_id")
                    or item.get("id")
                )

                if not external_id:
                    raise CommandError(
                        f"Item #{position} "
                        "has no source_id"
                    )

                source_key = (
                    f"{source}:{external_id}"
                )

                if len(source_key) > 255:
                    raise CommandError(
                        f"Item #{position} source ID "
                        "is longer than 255 characters"
                    )

                title = compact(
                    item.get("title"),
                    255,
                )

                if not title:
                    raise CommandError(
                        f"Item #{position} "
                        "has no title"
                    )

                raw_body = (
                    item.get("body")
                    or item.get("content")
                    or ""
                )

                content = render_plain_markdown(
                    raw_body
                )

                source_urls = normalize_source_urls(
                    item.get("source_urls")
                    or item.get("source_url")
                )

                source_note = compact(
                    item.get("source_note"),
                    4000,
                )

                meta_description = (
                    clean_meta_description(
                        item.get(
                            "meta_description"
                        ),
                        raw_body,
                    )
                )

                image_topic = compact(
                    item.get("image_topic"),
                    64,
                )

                existing = News.objects.filter(
                    generated_source_id=source_key,
                ).first()

                if existing:
                    slug = existing.slug
                    published = (
                        True
                        if options["publish"]
                        else existing.is_published
                    )
                    time_create = (
                        existing.time_create
                    )
                else:
                    slug = unique_slug(
                        item.get("slug"),
                        title,
                        source_key,
                    )
                    published = bool(
                        options["publish"]
                    )
                    time_create = parse_timestamp(
                        item.get("published_at")
                        or item.get("created_at")
                        or payload.get("created_at")
                    )

                values = {
                    "title": title,
                    "slug": slug,
                    "content": content,
                    "meta_description": (
                        meta_description
                    ),
                    "generated_source_id": (
                        source_key
                    ),
                    "source_note": source_note,
                    "source_urls": source_urls,
                    "image_topic": image_topic,
                    "cat": category,
                    "time_create": time_create,
                    "is_published": published,
                }

                if existing is None:
                    values["imported_at"] = (
                        timezone.now()
                    )

                    News.objects.create(
                        **values
                    )

                    counters["created"] += 1
                    continue

                changed = False

                for field_name, value in (
                    values.items()
                ):
                    if (
                        getattr(
                            existing,
                            field_name,
                        )
                        != value
                    ):
                        setattr(
                            existing,
                            field_name,
                            value,
                        )
                        changed = True

                if not changed:
                    counters[
                        "unchanged"
                    ] += 1
                    continue

                existing.imported_at = (
                    timezone.now()
                )
                existing.save()

                counters["updated"] += 1

            if options["dry_run"]:
                transaction.set_rollback(
                    True
                )

        mode = (
            "DRY RUN"
            if options["dry_run"]
            else "COMPLETED"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: "
                f"created={counters['created']} "
                f"updated={counters['updated']} "
                f"unchanged={counters['unchanged']}"
            )
        )
