from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import secrets

class BucketList(models.Model):
    """
    Model for main BucketList container
    """
    class Meta:
        ordering = ["-created_at"]
      
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_bucketlists",
    )
      
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    decision_deadline = models.DateTimeField(null=True, blank=True)
    allow_viewer_voting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    
    # New scheduling fields
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    @property
    def is_frozen(self):
        if not self.decision_deadline:
            return False
        return timezone.now() >= self.decision_deadline
    
    @property
    def is_date_range(self):
        return bool(self.start_date and self.end_date and self.start_date != self.end_date)

    @property
    def has_time(self):
        return bool(self.start_time or self.end_time)

    def clean(self):
        errors = {}

        if self.end_date and not self.start_date:
            errors["end_date"] = "End date cannot be set without a start date."
    
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date cannot be earlier than start date."
    
        if self.start_time and not self.start_date:
            errors["start_time"] = "Start time requires a start date."
    
        if self.end_time and not self.start_date:
            errors["end_time"] = "End time requires a start date."
    
        if self.start_time and not self.end_time:
            errors["end_time"] = "End time is required when a start time is provided."
    
        if self.end_time and not self.start_time:
            errors["start_time"] = "Start time is required when an end time is provided."
    
        effective_end_date = self.end_date or self.start_date
    
        if (
            self.start_date
            and effective_end_date == self.start_date
            and self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            errors["end_time"] = "End time must be later than start time for a single-day event."
    
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BucketListMembership(models.Model):
    """
    Define roles within a list
    """
    class RoleChoices(models.TextChoices):
        OWNER = "owner", "Owner"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"
        
    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bucket_list", "user"],
                name="unique_membership_per_user_per_list"
            )
        ]
    
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="memberships" #bucket_list.memberships
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bucketlist_memberships", #user.bucketlist_memberships
    )
    
    role = models.CharField(
        max_length=20, 
        choices=RoleChoices.choices,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
        
    def __str__(self):
        return f"{self.user} - {self.bucket_list} ({self.role})"
    

class BucketListItem(models.Model):
    """
    Entries on a bucketlist
    """
    class StatusChoices(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        LOCKED_IN = "locked_in", "Locked In"
        COMPLETE = "complete", "Complete"
        
    class Meta:
        ordering = ["-created_at"]
        
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_bucketlist_items",
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PROPOSED,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New scheduling fields
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    @property
    def upvotes_count(self):
        return self.votes.filter(vote_type=ItemVote.VoteTypeChoices.UPVOTE).count()
    
    @property
    def downvotes_count(self):
        return self.votes.filter(vote_type=ItemVote.VoteTypeChoices.DOWNVOTE).count()
    
    @property
    def score(self):
        return self.upvotes_count - self.downvotes_count
    
    @property
    def is_date_range(self):
        return bool(self.start_date and self.end_date and self.start_date != self.end_date)

    @property
    def has_time(self):
        return bool(self.start_time or self.end_time)

    def clean(self):
        errors = {}

        if self.end_date and not self.start_date:
            errors["end_date"] = "End date cannot be set without a start date."
    
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date cannot be earlier than start date."
    
        if self.start_time and not self.start_date:
            errors["start_time"] = "Start time requires a start date."
    
        if self.end_time and not self.start_date:
            errors["end_time"] = "End time requires a start date."
    
        if self.start_time and not self.end_time:
            errors["end_time"] = "End time is required when a start time is provided."
    
        if self.end_time and not self.start_time:
            errors["start_time"] = "Start time is required when an end time is provided."
    
        effective_end_date = self.end_date or self.start_date
    
        if (
            self.start_date
            and effective_end_date == self.start_date
            and self.start_time
            and self.end_time
            and self.end_time <= self.start_time
        ):
            errors["end_time"] = "End time must be later than start time for a single-day item."
    
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        if self.status == self.StatusChoices.COMPLETE and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != self.StatusChoices.COMPLETE:
            self.completed_at = None

        self.full_clean()
        super().save(*args, **kwargs)
        
class ItemVote(models.Model):
    class VoteTypeChoices(models.TextChoices):
        UPVOTE = "upvote", "Upvote"
        DOWNVOTE = "downvote", "Downvote"
        
    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "user"],
                name="unique_vote_per_user_per_item",
            )
        ]
        
    item = models.ForeignKey(
        BucketListItem,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="item_votes",
    )
    vote_type = models.CharField(
        max_length=10,
        choices=VoteTypeChoices.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user} - {self.item} ({self.vote_type})"
    

class BucketListInvite(models.Model):
    class InviteRoleChoices(models.TextChoices):
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"
        
    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bucket_list", "role"],
                name="unique_invite_role_per_bucket_list"
            )
        ]
        
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    role = models.CharField(
        max_length=20,
        choices=InviteRoleChoices.choices,
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
    )
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.bucket_list} - {self.role} invite"
    
    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
    
    @property
    def is_valid(self):
        return self.is_active and not self.is_expired
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    def set_expiry(self, days=7):
        self.expires_at = timezone.now() + timedelta(days=days)
        
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        if not self.expires_at:
            self.set_expiry()
        super().save(*args, **kwargs)
        
    def regenerate(self):
        self.token = self.generate_token()
        self.is_active = True
        self.set_expiry()
        self.save()
        
class Notification(models.Model):
    """
    In-app noifications for bucket list members.
    Created by signals and the freeze_reminder management command.
    """
    
    class TypeChoices(models.TextChoices):
        ITEM_ADDED = "item_added", "Item Added"
        ITEM_LOCKED_IN = "item_locked_in", "Item Locked In"
        ITEM_COMPLETED = "item_completed", "Item Completed"
        LIST_FROZEN = "list_frozen", "List Frozen"
        FREEZE_REMINDER = "freeze_reminder", "Freeze Reminder"
        
    class Meta:
        ordering = ["-created_at"]
        
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=TypeChoices.choices,
    )
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    item = models.ForeignKey(
        BucketListItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.notification_type}] → {self.recipient} — {self.message[:60]}"
