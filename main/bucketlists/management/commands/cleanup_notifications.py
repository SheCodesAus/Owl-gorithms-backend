from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
 
from bucketlists.models import Notification
 
 
class Command(BaseCommand):
    help = "Delete notifications older than 30 days."
 
    RETENTION_DAYS = 30
 
    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=self.RETENTION_DAYS)
 
        deleted_count, _ = Notification.objects.filter(
            created_at__lt=cutoff,
        ).delete()
 
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} notification(s) older than {self.RETENTION_DAYS} days."
            )
        )
