from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers
from users.serializers import UserBasicSerializer

from .models import BucketList, BucketListMembership, BucketListItem, ItemVote, BucketListInvite, Notification

class BucketListMembershipSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = BucketListMembership
        fields = [
            "id",
            "user",
            "role",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "joined_at",
        ]
        
class BucketListItemSerializer(serializers.ModelSerializer):
    creator = UserBasicSerializer(source="created_by", read_only=True)
    creator_email = serializers.EmailField(source="created_by.email", read_only=True)
    upvotes_count = serializers.IntegerField(read_only=True)
    downvotes_count = serializers.IntegerField(read_only=True)
    score = serializers.IntegerField(read_only=True)
    user_vote = serializers.SerializerMethodField()
    is_date_range = serializers.ReadOnlyField()
    has_time = serializers.ReadOnlyField()
    
    class Meta:
        model = BucketListItem
        fields = [
            "id",
            "bucket_list",
            "creator",
            "creator_email",
            "title",
            "description",
            "status",
            "completed_at",
            "upvotes_count",
            "downvotes_count",
            "score",
            "user_vote",
            "created_at",
            "updated_at",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "is_date_range",
            "has_time",
        ]
        read_only_fields = [
            "id",
            "bucket_list",
            "creator",
            "creator_email",
            "completed_at",
            "upvotes_count",
            "downvotes_count",
            "score",
            "user_vote",
            "created_at",
            "updated_at",
            "is_date_range",
            "has_time",
        ]
        
    def get_user_vote(self, obj):
        request = self.context.get("request")
        
        if not request or not request.user.is_authenticated:
            return None
        
        vote = obj.votes.filter(user=request.user).first()
        
        if vote:
            return vote.vote_type
        
        return None
    
    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        errors = {}

        if end_date and not start_date:
            errors["end_date"] = "End date cannot be set without a start date."

        if start_date and end_date and end_date < start_date:
            errors["end_date"] = "End date cannot be earlier than start date."

        if start_time and not start_date:
            errors["start_time"] = "Start time requires a start date."

        if end_time and not start_date:
            errors["end_time"] = "End time requires a start date."

        if start_time and not end_time:
            errors["end_time"] = "End time is required when a start time is provided."

        if end_time and not start_time:
            errors["start_time"] = "Start time is required when an end time is provided."

        effective_end_date = end_date or start_date

        if (
            start_date
            and effective_end_date == start_date
            and start_time
            and end_time
            and end_time <= start_time
        ):
            errors["end_time"] = "End time must be later than start time for a single-day item."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

class BucketListSerializer(serializers.ModelSerializer):
    owner = UserBasicSerializer(read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    memberships = BucketListMembershipSerializer(many=True, read_only=True)
    items = BucketListItemSerializer(many=True, read_only=True)
    is_frozen = serializers.ReadOnlyField()
    is_date_range = serializers.ReadOnlyField()
    has_time = serializers.ReadOnlyField()
    
    class Meta:
        model = BucketList
        fields = [
            "id",
            "owner",
            "owner_email",
            "title",
            "description",
            "decision_deadline",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "is_date_range",
            "has_time",
            "allow_viewer_voting",
            "is_frozen",
            "is_public",
            "memberships",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_email",
            "is_date_range",
            "has_time",
            "is_frozen",
            "memberships",
            "items",
            "created_at",
            "updated_at",
        ]
        
    def validate_decision_deadline(self, value):
        if value is not None:
            if value <= timezone.now():
                raise serializers.ValidationError(
                    "Decision deadline must be in the future."
                )
        return value
    
    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))

        errors = {}

        if end_date and not start_date:
            errors["end_date"] = "End date cannot be set without a start date."

        if start_date and end_date and end_date < start_date:
            errors["end_date"] = "End date cannot be earlier than start date."

        if start_time and not start_date:
            errors["start_time"] = "Start time requires a start date."

        if end_time and not start_date:
            errors["end_time"] = "End time requires a start date."

        if start_time and not end_time:
            errors["end_time"] = "End time is required when a start time is provided."

        if end_time and not start_time:
            errors["start_time"] = "Start time is required when an end time is provided."

        effective_end_date = end_date or start_date

        if (
            start_date
            and effective_end_date == start_date
            and start_time
            and end_time
            and end_time <= start_time
        ):
            errors["end_time"] = "End time must be later than start time for a single-day event."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        
        bucket_list = BucketList.objects.create(
            owner=user,
            **validated_data
        )
        
        BucketListMembership.objects.create(
            bucket_list=bucket_list,
            user=user,
            role=BucketListMembership.RoleChoices.OWNER,
        )
        
        return bucket_list
    
class ItemVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVote
        fields = [
            "id",
            "item",
            "user",
            "vote_type",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "item",
            "user",
            "created_at",
            "updated_at"
        ]
        
class BucketListInviteSerializer(serializers.ModelSerializer):
    invite_url = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = BucketListInvite
        fields = [
            "id",
            "bucket_list",
            "role",
            "token",
            "invite_url",
            "expires_at",
            "is_active",
            "is_expired",
            "is_valid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "bucket_list",
            "role",
            "token",
            "invite_url",
            "expires_at",
            "is_active",
            "is_expired",
            "is_valid",
            "created_at",
            "updated_at",
        ]
        
    def get_invite_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return f"{settings.FRONTEND_URL}/invites/{obj.token}"
    
class InviteAcceptSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    
    def validate_accept(self, value):
        if value is not True:
            raise serializers.ValidationError("You must accept the invite to join the list.")
        return value
    
    
class BucketListMembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BucketListMembership
        fields = ["role"]
        
    def validate_role(self, value):
        allowed_roles = [
            BucketListMembership.RoleChoices.EDITOR,
            BucketListMembership.RoleChoices.VIEWER,
        ]
        
        if value not in allowed_roles:
            raise serializers.ValidationError(
                "Role must be either 'editor' or 'viewer'."
            )
            
        return value
    
    
class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    bucket_list_title = serializers.CharField(
        source="bucket_list.title", read_only=True, default=None
    )
    item_title = serializers.CharField(
        source="item.title", read_only=True, default=None
    )
    bucket_list_id = serializers.IntegerField(
        source="bucket_list.id", read_only=True, default=None
    )
    item_id = serializers.IntegerField(
        source="item.id", read_only=True, default=None
    )
    
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "message",
            "is_read",
            "actor_name",
            "bucket_list_id",
            "bucket_list_title",
            "item_id",
            "item_title",
            "created_at",
        ]
        read_only_fields = fields
 
    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        if hasattr(obj.actor, "display_name") and obj.actor.display_name:
            return obj.actor.display_name
        return obj.actor.username