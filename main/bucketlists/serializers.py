from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import BucketList, BucketListMembership, BucketListItem

class BucketListMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    
    class Meta:
        model = BucketListMembership
        fields = [
            "id",
            "user_id",
            "user_email",
            "role",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "user_email",
            "joined_at",
        ]
        
class BucketListItemSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    upvotes_count = serializers.IntegerField(read_only=True)
    downvotes_count = serializers.IntegerField(read_only=True)
    score = serializers.IntegerField(read_only=True)
    
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
            "created_at",
            "updated_at",
        ]
        
class BucketListSerializer(serializers.ModelSerializer):
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