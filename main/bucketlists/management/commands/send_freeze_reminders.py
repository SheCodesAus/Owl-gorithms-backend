# bucketlists/management/commands/send_freeze_reminders.py
#
# Run manually:    python manage.py send_freeze_reminders
# Run via cron:    0 * * * * cd /path/to/project && python manage.py send_freeze_reminders
# (runs every hour)

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from bucketlists.models import BucketList, Notification
from bucketlists.notification_services import notify_freeze_reminder


class Command(BaseCommand):
    help = "Send freeze reminder notifications for bucket lists with upcoming deadlines."

    # Remind at these thresholds (hours before deadline)
    REMINDER_THRESHOLDS = [48, 24]

    def handle(self, *args, **options):
        now = timezone.now()
        sent_count = 0

        for hours in self.REMINDER_THRESHOLDS:
            window_start = now + timedelta(hours=hours - 1)
            window_end = now + timedelta(hours=hours)

            # Lists whose deadline falls within the next window
            lists_due = BucketList.objects.filter(
                decision_deadline__gte=window_start,
                decision_deadline__lt=window_end,
                # Only lists that aren't already frozen
            ).exclude(
                decision_deadline__lte=now,
            )

            for bucket_list in lists_due:
                # Skip if we've already sent a reminder at this threshold
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
                sent_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Sent {hours}h reminder for: {bucket_list.title}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Done. {sent_count} reminder(s) sent.")
        )