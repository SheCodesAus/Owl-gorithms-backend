"""
Signals for automatic notification creation.

Connected in BucketlistsConfig.ready() inside apps.py.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import BucketListItem, BucketList
from .notification_services import (
    notify_item_added,
    notify_item_status_changed,
    notify_list_frozen,
)


# Track the previous status before a save so we can detect changes
_item_previous_status = {}
_list_previous_frozen = {}


@receiver(pre_save, sender=BucketListItem)
def capture_item_previous_status(sender, instance, **kwargs):
    """
    Store the current status before saving so post_save can
    detect whether status actually changed.
    """
    if instance.pk:
        try:
            previous = BucketListItem.objects.get(pk=instance.pk)
            _item_previous_status[instance.pk] = previous.status
        except BucketListItem.DoesNotExist:
            pass


@receiver(post_save, sender=BucketListItem)
def handle_item_saved(sender, instance, created, **kwargs):
    """
    Fire item_added on create.
    Fire item_locked_in / item_completed on status change.
    """
    actor = getattr(instance, "_actor", None)

    if created:
        if actor:
            notify_item_added(instance, actor)
        return

    # Status change detection
    previous_status = _item_previous_status.pop(instance.pk, None)
    if previous_status is None:
        return

    if previous_status != instance.status and instance.status in ("locked_in", "complete"):
        notify_item_status_changed(instance, actor)


@receiver(pre_save, sender=BucketList)
def capture_list_frozen_state(sender, instance, **kwargs):
    """
    Store whether the list was already frozen before this save.
    """
    if instance.pk:
        try:
            previous = BucketList.objects.get(pk=instance.pk)
            _list_previous_frozen[instance.pk] = previous.is_frozen
        except BucketList.DoesNotExist:
            pass


@receiver(post_save, sender=BucketList)
def handle_list_saved(sender, instance, created, **kwargs):
    """
    Fire list_frozen when a list transitions from not-frozen to frozen.
    This happens when decision_deadline is set to a past time (or passes).
    """
    if created:
        return

    was_frozen = _list_previous_frozen.pop(instance.pk, False)
    is_now_frozen = instance.is_frozen

    if not was_frozen and is_now_frozen:
        notify_list_frozen(instance)