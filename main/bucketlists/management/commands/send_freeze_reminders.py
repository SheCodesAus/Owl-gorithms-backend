from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
 
from bucketlists.models import BucketList, Notification
from bucketlists.notification_services import (
    notify_freeze_reminder,
    notify_list_frozen,
)
 
 
class Command(BaseCommand):
    help = "Auto-freeze lists past their deadline and send upcoming freeze reminders."
 
    REMINDER_THRESHOLDS = [48, 24]
 
    def handle(self, *args, **options):
        now = timezone.now()
        frozen_count = 0
        reminder_count = 0
 
        # ── 1. Auto-freeze lists whose deadline has passed ────────────────
        lists_to_freeze = BucketList.objects.filter(
            is_frozen=False,
            decision_deadline__isnull=False,
            decision_deadline__lte=now,
        )
 
        for bucket_list in lists_to_freeze:
            bucket_list.is_frozen = True
            bucket_list.save(update_fields=["is_frozen"])
            notify_list_frozen(bucket_list)
            frozen_count += 1
            self.stdout.write(
                self.style.SUCCESS(f"  Frozen: {bucket_list.title}")
            )
 
        # ── 2. Send reminders for upcoming deadlines ──────────────────────
        for hours in self.REMINDER_THRESHOLDS:
            window_start = now + timedelta(hours=hours - 1)
            window_end = now + timedelta(hours=hours)
 
            lists_due = BucketList.objects.filter(
                is_frozen=False,
                decision_deadline__gte=window_start,
                decision_deadline__lt=window_end,
            )
 
            for bucket_list in lists_due:
                already_reminded = Notification.objects.filter(
                    bucket_list=bucket_list,
                    notification_type=Notification.TypeChoices.FREEZE_REMINDER,
                    created_at__gte=window_start - timedelta(hours=2),
                ).exists()
 
                if already_reminded:
                    self.stdout.write(
                        f"  Skipping {bucket_list.title} — already reminded at {hours}h"
                    )
                    continue
 
                notify_freeze_reminder(bucket_list, hours_remaining=hours)
                reminder_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Sent {hours}h reminder for: {bucket_list.title}"
                    )
                )
 
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {frozen_count} list(s) frozen, {reminder_count} reminder(s) sent."
            )
        )
