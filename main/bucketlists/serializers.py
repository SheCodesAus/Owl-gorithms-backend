from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers
from datetime import datetime, time
from users.serializers import UserBasicSerializer

from .models import BucketList, BucketListMembership, BucketListItem, ItemVote, BucketListInvite, Notification, Reaction

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
    reactions_summary = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    
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
            "reactions_summary",
            "user_reaction",
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
    
    def get_reaction_summary(self, obj):
        """
        Returns a count of each reaction type for this item.
        """
        counts = {choice[0]: 0 for choice in Reaction.REACTION_CHOICES}
        for reaction in obj.reactions.all():
            if reaction.reaction_type in counts:
                counts[reaction.reaction_type] += 1
        return counts
    
    def get_user_reaction(self, obj):
        """
        Returns current user reaction type, or None.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        reaction = obj.reactions.filter(user=request.user).first()
        return reaction.reaction_type if reaction else None
        
    
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
    decision_deadline = serializers.SerializerMethodField(read_only=True)
    decision_deadline_input = serializers.DateField(
        write_only=True,
        required=False,
        allow_null=True
    )
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
            "decision_deadline_input",
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
        if value is None:
            return value

        if isinstance(value, datetime):
            deadline_dt = value
        else:
            deadline_dt = datetime.combine(value, time(23, 59, 59))

        if timezone.is_naive(deadline_dt):
            deadline_dt = timezone.make_aware(
                deadline_dt,
                timezone.get_current_timezone()
            )

        if deadline_dt <= timezone.now():
            raise serializers.ValidationError(
                "Decision deadline must be in the future."
            )

        return deadline_dt
    
    def get_decision_deadline(self, obj):
        if not obj.decision_deadline:
            return None
        return timezone.localtime(obj.decision_deadline).date().isoformat()

    def validate(self, attrs):
        deadline_date = attrs.pop("decision_deadline_input", serializers.empty)

        if deadline_date is not serializers.empty:
            if deadline_date is None:
                attrs["decision_deadline"] = None
            else:
                deadline_dt = datetime.combine(deadline_date, time(23, 59, 59))

                if timezone.is_naive(deadline_dt):
                    deadline_dt = timezone.make_aware(
                        deadline_dt,
                        timezone.get_current_timezone()
                    )

                if deadline_dt <= timezone.now():
                    raise serializers.ValidationError({
                        "decision_deadline": "Decision deadline must be in the future."
                    })

                attrs["decision_deadline"] = deadline_dt

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
    item_score = serializers.SerializerMethodField()
    item_user_vote = serializers.SerializerMethodField()
 
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "message",
            "is_read",
            "is_dismissed",
            "actor_name",
            "bucket_list_id",
            "bucket_list_title",
            "item_id",
            "item_title",
            "item_score",
            "item_user_vote",
            "created_at",
        ]
        read_only_fields = fields
 
    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        actor = obj.actor
        first = actor.first_name or ""
        last_initial = f"{actor.last_name[0]}." if actor.last_name else ""
        name = f"{first} {last_initial}".strip()
        if name:
            return name
        if actor.email:
            return actor.email.split("@")[0]
        return actor.username
 
    def get_item_score(self, obj):
        if not obj.item:
            return None
        return obj.item.score
 
    def get_item_user_vote(self, obj):
        if not obj.item:
            return None
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        vote = obj.item.votes.filter(user=request.user).first()
        return vote.vote_type if vote else None

class BucketListFreezeSerializer(serializers.Serializer):
    is_frozen = serializers.BooleanField()