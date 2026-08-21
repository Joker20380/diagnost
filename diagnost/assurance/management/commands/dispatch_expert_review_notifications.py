import time

from django.core.management.base import BaseCommand, CommandError

from assurance.notifications import dispatch_expert_review_notifications


class Command(BaseCommand):
    help = "Deliver queued remote expert-review email notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=30)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 1000:
            raise CommandError("--limit must be between 1 and 1000")
        interval = options["interval"]
        if interval < 5 or interval > 3600:
            raise CommandError("--interval must be between 5 and 3600 seconds")
        while True:
            result = dispatch_expert_review_notifications(limit=limit)
            self._report(result)
            if not options["watch"]:
                break
            time.sleep(interval)

    def _report(self, result):
        self.stdout.write(
            (
                f"Expert review notifications: sent={result['sent']}, "
                f"failed={result['failed']}"
            )
        )
