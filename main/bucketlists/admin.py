from django.contrib import admin
from .models import (
    BucketList,
    BucketListInvite,
    BucketListItem,
    BucketListMembership,
    ItemVote,
)


@admin.register(BucketList)
class BucketListAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "owner",
        "decision_deadline",
        "allow_viewer_voting",
        "created_at",
    )
    list_filter = ("allow_viewer_voting", "created_at")
    search_fields = ("title", "owner__email", "owner__username")


@admin.register(BucketListMembership)
class BucketListMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "bucket_list", "user", "role", "joined_at")
    list_filter = ("role", "joined_at")
    search_fields = ("bucket_list__title", "user__email", "user__username")


@admin.register(BucketListItem)
class BucketListItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "bucket_list", "created_by", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "bucket_list__title", "created_by__email", "created_by__username")


@admin.register(ItemVote)
class ItemVoteAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "user", "vote_type", "updated_at")
    list_filter = ("vote_type", "updated_at")
    search_fields = ("item__title", "user__email", "user__username")


@admin.register(BucketListInvite)
class BucketListInviteAdmin(admin.ModelAdmin):
    list_display = ("id", "bucket_list", "role", "is_active", "expires_at", "updated_at")
    list_filter = ("role", "is_active", "expires_at")
    search_fields = ("bucket_list__title", "token")