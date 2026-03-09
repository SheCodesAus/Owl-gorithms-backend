from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from users.serializers import UserBasicSerializer

from .models import BucketList, BucketListMembership, BucketListItem, ItemVote, BucketListInvite

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
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    upvotes_count = serializers.IntegerField(read_only=True)
    downvotes_count = serializers.IntegerField(read_only=True)
    score = serializers.IntegerField(read_only=True)
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = BucketListItem
        fields = [
            "id",
            "bucket_list",
            "created_by",
            "created_by_email",
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
        ]
        read_only_fields = [
            "id",
            "bucket_list",
            "created_by",
            "created_by_email",
            "completed_at",
            "upvotes_count",
            "downvotes_count",
            "score",
            "user_vote",
            "created_at",
            "updated_at",
        ]
        
    def get_user_vote(self, obj):
        request = self.context.get("request")
        
        if not request or not request.user.is_authenticated:
            return None
        
        vote = obj.votes.filter(user=request.user).first()
        
        if vote:
            return vote.vote_type
        
        return None
        
class BucketListSerializer(serializers.ModelSerializer):
    owner = UserBasicSerializer(read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    memberships = BucketListMembershipSerializer(many=True, read_only=True)
    items = BucketListItemSerializer(many=True, read_only=True)
    is_frozen = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = BucketList
        fields = [
            "id",
            "owner",
            "owner_email",
            "title",
            "description",
            "decision_deadline",
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
        return request.build_absolute_uri(f"/invites/{obj.token}/")
    
class InviteAcceptSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    
    def validate_accept(self, value):
        if value is not True:
            raise serializers.ValidationError("You must accept the invite to join the list.")
        return value