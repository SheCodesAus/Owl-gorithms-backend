"""
Notification service layer.
All notification creation goes through here — signals and management
commands both call these functions. Never create Notification rows directly.
"""

from .models import BucketListMembership, Notification


def get_list_members(bucket_list):
    """Return all users who are members of this bucket list."""
    return [
        membership.user
        for membership in bucket_list.memberships.select_related("user").all()
    ]


def create_notifications_for_members(
    *,
    bucket_list,
    notification_type,
    message,
    actor=None,
    item=None,
    exclude_actor=True,
):
    """
    Create one Notification row per member of the bucket list.

    Args:
        bucket_list: BucketList instance
        notification_type: one of Notification.TypeChoices
        message: pre-rendered string shown in the UI
        actor: User who triggered the event (excluded from recipients by default)
        item: BucketListItem instance if relevant, else None
        exclude_actor: if True, the actor does not receive their own notification
    """
    members = get_list_members(bucket_list)

    notifications = []
    for member in members:
        if exclude_actor and actor and member == actor:
            continue

        notifications.append(
            Notification(
                recipient=member,
                actor=actor,
                notification_type=notification_type,
                bucket_list=bucket_list,
                item=item,
                message=message,
            )
        )

    if notifications:
        Notification.objects.bulk_create(notifications)


# ── Individual event helpers ──────────────────────────────────────────────────

def notify_item_added(item, actor):
    actor_name = actor.display_name if hasattr(actor, "display_name") and actor.display_name else actor.first_name
    create_notifications_for_members(
        bucket_list=item.bucket_list,
        notification_type=Notification.TypeChoices.ITEM_ADDED,
        message=f"{actor_name} added \"{item.title}\" to {item.bucket_list.title}.",
        actor=actor,
        item=item,
    )


def notify_item_status_changed(item, actor):
    actor_name = actor.display_name if hasattr(actor, "display_name") and actor.display_name else actor.username

    if item.status == "locked_in":
        notification_type = Notification.TypeChoices.ITEM_LOCKED_IN
        message = f"\"{item.title}\" has been locked in on {item.bucket_list.title}!"
    elif item.status == "complete":
        notification_type = Notification.TypeChoices.ITEM_COMPLETED
        message = f"\"{item.title}\" has been completed on {item.bucket_list.title}! 🎉"
    else:
        return  # proposed — no notification needed

    create_notifications_for_members(
        bucket_list=item.bucket_list,
        notification_type=notification_type,
        message=message,
        actor=actor,
        item=item,
        exclude_actor=False,  # everyone gets status change notifications including the actor
    )


def notify_list_frozen(bucket_list):
    create_notifications_for_members(
        bucket_list=bucket_list,
        notification_type=Notification.TypeChoices.LIST_FROZEN,
        message=f"Time's up! {bucket_list.title} is now frozen!",
        exclude_actor=False,  # everyone including owner gets this
    )


def notify_freeze_reminder(bucket_list, hours_remaining):
    """Called by the management command for upcoming freeze deadlines."""
    if hours_remaining <= 24:
        time_str = f"{int(hours_remaining)} hour{'s' if hours_remaining != 1 else ''}"
    else:
        days = round(hours_remaining / 24)
        time_str = f"{days} day{'s' if days != 1 else ''}"

    create_notifications_for_members(
        bucket_list=bucket_list,
        notification_type=Notification.TypeChoices.FREEZE_REMINDER,
        message=f"{bucket_list.title} will freeze in {time_str}! Hurry and get your votes in.",
        exclude_actor=False,
    )