from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import ExpertReviewNotification


MAX_ATTEMPTS = 5


def _message(notification):
    path = reverse("assurance:case_detail", args=[notification.repair_case_id])
    base_url = getattr(settings, "ASSURANCE_REVIEW_BASE_URL", "").rstrip("/")
    url = f"{base_url}{path}" if base_url else path
    operation = notification.case_operation.operation
    subject = f"Expert review required: case #{notification.repair_case_id}"
    body = (
        f"Operation '{operation.title}' ({operation.key}) requires expert review.\n"
        f"Repair case: #{notification.repair_case_id}\n"
        f"Review: {url}\n"
    )
    return subject, body


def dispatch_expert_review_notifications(*, limit=50, now=None):
    now = now or timezone.now()
    processed = {"sent": 0, "failed": 0}
    for _ in range(limit):
        with transaction.atomic():
            notification = (
                ExpertReviewNotification.objects.select_for_update(skip_locked=True)
                .select_related("case_operation__operation")
                .filter(
                    status__in=[
                        ExpertReviewNotification.Status.QUEUED,
                        ExpertReviewNotification.Status.FAILED,
                    ],
                    attempts__lt=MAX_ATTEMPTS,
                    next_attempt_at__lte=now,
                )
                .order_by("next_attempt_at", "id")
                .first()
            )
            if notification is None:
                break
            notification.attempts += 1
            try:
                subject, body = _message(notification)
                delivered = send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [notification.recipient_email],
                    fail_silently=False,
                )
                if delivered != 1:
                    raise RuntimeError("Email backend did not confirm delivery.")
            except Exception as exc:
                notification.status = ExpertReviewNotification.Status.FAILED
                notification.last_error = str(exc)[:2000]
                notification.next_attempt_at = now + timedelta(
                    minutes=min(2 ** notification.attempts, 60)
                )
                notification.save(
                    update_fields=["status", "attempts", "last_error", "next_attempt_at"]
                )
                processed["failed"] += 1
            else:
                notification.status = ExpertReviewNotification.Status.SENT
                notification.sent_at = now
                notification.last_error = ""
                notification.save(
                    update_fields=["status", "attempts", "sent_at", "last_error"]
                )
                processed["sent"] += 1
    return processed
