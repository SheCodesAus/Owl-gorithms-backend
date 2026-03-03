from rest_framework import serializers
from .models import BucketList, BucketItem, BucketListMember

class BucketListMemberSerializer(serializers.ModelSerializer):
    # Show basic member info without nesting whole user serializer
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    
    class Meta:
        model = BucketListMember
        fields = "__all__"
        read_only_fields = [
            "id",
            "user_id",
            "username",
            "joined_at",
        ]

class BucketListSerializer(serializers.ModelSerializer):
    
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    
    #show members + roles
    memberships = BucketListMemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = BucketList
        fields = "__all__"
        read_only_fields = [
            "id",
            "date_created",
            "owner",
            "owner_id",
            "owner_username"]
        
class BucketItemSerializer(serializers.ModelSerializer):
    bucket_list_id = serializers.IntegerField(source="bucket_list.id", read_only=True)
    created_by_id = serializers.IntegerField(source="created_by.id", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    
    class Meta:
        model = BucketItem
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_by",
            "created_by_id",
            "created_by_username",
            "date_created",
            "date_updated",
            "completed_at",
            "bucket_list_id",
        ]