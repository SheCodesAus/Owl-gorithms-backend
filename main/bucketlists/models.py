from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
class BucketList(models.Model):
        CATEGORY_CHOICES = [
            ("one", "One"),
            ("two", "Two"),
            ("three", "Three"),
        ]
        
        title = models.CharField(max_length=200)
        description = models.TextField(blank=True)
        image = models.URLField(null=True, blank=True)
        date_created = models.DateTimeField(auto_now_add=True)
        category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
        
        is_open = models.BooleanField(default=True)
        is_public = models.BooleanField(default=False)
        has_deadline = models.BooleanField(default=False)
        deadline = models.DateTimeField(null=True, blank=True)
        
        owner = models.ForeignKey(
            settings.AUTH_USER_MODEL, #Better than pointing directly to User model incase it changes in the future
            on_delete=models.CASCADE,
            related_name="owned_bucketlists",
        )
        
        # Users who are part of this bucketlist (contributor/viewer)
        members = models.ManyToManyField(
            settings.AUTH_USER_MODEL,
            through="BucketListMember",
            related_name="bucketlists",
            blank=True,
        )
        
        def __str__(self):
            return self.title
        
        def clean(self):
            """
            Optional housekeeping
            Keeps data consistent
            If has_deadline is False, deadline should be empty
            Can add more
            """
            if not self.has_deadline:
                self.deadline = None
                
class BucketListMember(models.Model):
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    
    ROLE_CHOICES = [
        (CONTRIBUTOR, "Contributor"),
        (VIEWER, "Viewer"),
    ]
    
    # one bucketlist can have many members
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="memberships" #bucket_list.memberships
    )
    
    # one user can have many memberships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bucketlist_memberships", #user.bucketlist_memberships
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CONTRIBUTOR)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("bucket_list", "user")
        
    def __str__(self):
        return f"{self.user} in {self.bucket_list} ({self.role})"
    

class BucketItem(models.Model):
    bucket_list = models.ForeignKey(
        BucketList,
        on_delete=models.CASCADE,
        related_name="items",
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.URLField(null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bucketitems",
    )
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def mark_completed(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        
    def mark_incomplete(self):
        self.is_completed = False
        self.completed_at = None