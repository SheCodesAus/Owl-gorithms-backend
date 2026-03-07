from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import BucketList, BucketListMembership, BucketListItem
from .serializers import BucketListSerializer, BucketListItemSerializer

class BucketListList(APIView):
    """
    GET all lists connected to a user.
    POST a new list (create)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        bucketlists = BucketList.objects.filter(
            memberships__user=request.user
        ).distinct()
        
        serializer = BucketListSerializer(bucketlists, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = BucketListSerializer(
            data=request.data,
            context={"request": request}
        )
        
        if serializer.is_valid():
            bucket_list = serializer.save()
            response_serializer = BucketListSerializer(
                bucket_list,
                context={"request": request}
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
class BucketListDetail(APIView):
    """
    GET one list (single) + Update/Delete
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return BucketList.objects.get(pk=pk, memberships__user=user)
        except BucketList.DoesNotExist:
            raise Http404
        
    def is_owner(self, bucket_list, user):
        return bucket_list.owner == user
    
    def get(self, request, pk):
        bucket_list = self.get_object(pk, request.user)
        serializer = BucketListSerializer(bucket_list, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
    def put(self, request, pk):
        bucket_list = self.get_object(pk, request.user)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can update this bucket list."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = BucketListSerializer(
            bucket_list,
            data=request.data,
            context={"request": request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
    def delete(self, request, pk):
        bucket_list = self.get_object(pk, request.user)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can delete this bucket list."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        bucket_list.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class BucketListItemListCreate(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_bucket_list(self, bucket_list_id, user):
        try:
            return BucketList.objects.get(
                pk=bucket_list_id,
                memberships__user=user
                )
        except BucketList.DoesNotExist:
            raise Http404
        
    def get_membership(self, bucket_list, user):
        try:
            return BucketListMembership.objects.get(
                bucket_list=bucket_list,
                user=user,
                )
        except BucketListMembership.DoesNotExist:
            raise Http404
        
    def get(self, request, bucket_list_id):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        items = bucket_list.items.all()
        serializer = BucketListItemSerializer(items, many=True, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
            )
        
    def post(self, request, bucket_list_id):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        membership = self.get_membership(bucket_list, request.user)
        
        if bucket_list.is_frozen and request.user != bucket_list.owner:
            return Response(
                {"detail": "This bucket list is frozen. New items can no longer be added."},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        if membership.role not in [
            BucketListMembership.RoleChoices.OWNER,
            BucketListMembership.RoleChoices.EDITOR,
        ]:
            return Response(
                {"detail": "You do not have permission to add items to this bucket list."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = BucketListItemSerializer(data=request.data, context={"request": request})
        
        if serializer.is_valid():
            item = serializer.save(
                bucket_list=bucket_list,
                created_by=request.user,
            )
            response_serializer = BucketListItemSerializer(item, context={"request": request})
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
class BucketListItemDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_item(self, pk, user):
        try:
            return BucketListItem.objects.get(
                pk=pk,
                bucket_list__memberships__user=user
            )
        except BucketListItem.DoesNotExist:
            raise Http404
        
    def get_membership(self, bucket_list, user):
        try:
            return BucketListMembership.objects.get(
                bucket_list=bucket_list,
                user=user,
            )
        except BucketListMembership.DoesNotExist:
            raise Http404
        
    def is_owner(self, bucket_list, user):
        return bucket_list.owner == user
    
    def can_edit_or_delete_item(self, item, user, membership):
        if self.is_owner(item.bucket_list, user):
            return True
        if item.bucket_list.is_frozen:
            return False
        
        if (
            membership.role == BucketListMembership.RoleChoices.EDITOR
            and item.created_by == user
        ):
            return True
        
        return False
    
    def get(self, request, pk):
        item = self.get_item(pk, request.user)
        serializer = BucketListItemSerializer(item, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
    def put(self, request, pk):
        item = self.get_item(pk, request.user)
        membership = self.get_membership(item.bucket_list, request.user)
        
        if not self.can_edit_or_delete_item(item, request.user, membership):
            return Response(
                {"detail": "You do not have permission to update this item."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        data = request.data.copy()
        
        if not self.is_owner(item.bucket_list, request.user) and "status" in data:
            return Response(
                {"detail": "Only the owner can change item status."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = BucketListItemSerializer(
            item,
            data=data,
            partial=True,
            context={"request": request},
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
    def delete(self, request, pk):
        item = self.get_item(pk, request.user)
        membership = self.get_membership(item.bucket_list, request.user)
        
        if not self.can_edit_or_delete_item(item, request.user, membership):
            return Response(
                {"detail": "You do not have permission to delete this item."},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)