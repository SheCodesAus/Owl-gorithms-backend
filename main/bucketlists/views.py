from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import BucketList, BucketListMembership, BucketListItem, ItemVote, BucketListInvite
from .serializers import BucketListSerializer, BucketListItemSerializer, ItemVoteSerializer, BucketListInviteSerializer, InviteAcceptSerializer, BucketListMembershipSerializer, BucketListMembershipUpdateSerializer

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
    
class ItemVoteAction(APIView):
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
        
    def can_vote(self, bucket_list, membership):
        if bucket_list.is_frozen:
            return False
        
        if membership.role in [
            BucketListMembership.RoleChoices.OWNER,
            BucketListMembership.RoleChoices.EDITOR,
        ]:
            return True
        
        if (
            membership.role == BucketListMembership.RoleChoices.VIEWER
            and bucket_list.allow_viewer_voting
        ):
            return True
        
        return False
    
    def post(self, request, pk):
        item = self.get_item(pk, request.user)
        membership = self.get_membership(item.bucket_list, request.user)
        
        if not self.can_vote(item.bucket_list, membership):
            return Response(
                {"detail": "You do not have permission to vote."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        vote_type = request.data.get("vote_type")
        
        if vote_type not in [
            ItemVote.VoteTypeChoices.UPVOTE,
            ItemVote.VoteTypeChoices.DOWNVOTE,
        ]:
            return Response(
                {"detail": "vote_type must be 'upvote' or 'downvote'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        vote, created = ItemVote.objects.update_or_create(
            item=item,
            user=request.user,
            defaults={"vote_type": vote_type},
        )
        
        serializer = ItemVoteSerializer(vote, context={"request": request})
        
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
        
    def delete(self, request, pk):
        item = self.get_item(pk, request.user)
        membership = self.get_membership(item.bucket_list, request.user)
        
        if not self.can_vote(item.bucket_list, membership):
            return Response(
                {"detail": "You cannot remove a vote from this item."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            vote = ItemVote.objects.get(item=item, user=request.user)
        except ItemVote.DoesNotExist:
            return Response(
                {"detail": "You do not have a vote on this item."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        vote.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class BucketListInviteManage(APIView):
    """
    Get or Regenerate invite for a role
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_bucket_list(self, pk, user):
        try:
            return BucketList.objects.get(pk=pk, memberships__user=user)
        except BucketList.DoesNotExist:
            raise Http404
        
    def is_owner(self, bucket_list, user):
        return bucket_list.owner == user
    
    def get_valid_role(self, role):
        valid_roles = [
            BucketListInvite.InviteRoleChoices.EDITOR,
            BucketListInvite.InviteRoleChoices.VIEWER,
        ]
        if role not in valid_roles:
            raise Http404
        return role
    
    def get(self, request, bucket_list_id, role):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        role = self.get_valid_role(role)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can view invite links."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        invite = BucketListInvite.objects.filter(
            bucket_list=bucket_list,
            role=role,
        ).first()
        
        if not invite:
            return Response(
                {"detail": "No invite exists for this role yet."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = BucketListInviteSerializer(invite, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
    def post(self, request, bucket_list_id, role):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        role = self.get_valid_role(role)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can create invite links."},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        invite, created = BucketListInvite.objects.get_or_create(
            bucket_list=bucket_list,
            role=role,
        )
        
        if not created:
            serializer = BucketListInviteSerializer(invite, context={"request": request})
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
            
        serializer = BucketListInviteSerializer(invite, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
        
    def put(self, request, bucket_list_id, role):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        role = self.get_valid_role(role)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can regenerate invite links."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        invite, _ = BucketListInvite.objects.get_or_create(
            bucket_list=bucket_list,
            role=role,
        )
        
        invite.regenerate()
        
        serializer = BucketListInviteSerializer(invite, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
class BucketListInviteDetail(APIView):
    """
    Preview invite by token
    Useful when someone opens link and we want front end to show:
    List Title
    Role they'll join as
    If they're already a member
    """
    permission_classes = [permissions.AllowAny]
    
    def get_invite(self, token):
        try:
            return BucketListInvite.objects.select_related("bucket_list", "bucket_list__owner").get(token=token)
        except BucketListInvite.DoesNotExist:
            raise Http404
        
    def get(self, request, token):
        invite = self.get_invite(token)
        
        already_member = False
        if request.user.is_authenticated:
            already_member = BucketListMembership.objects.filter(
                bucket_list=invite.bucket_list,
                user=request.user,
            ).exists()
        
        serializer = BucketListInviteSerializer(invite, context={"request": request})
        
        data = serializer.data
        data["bucket_list_title"] = invite.bucket_list.title
        data["bucket_list_description"] = invite.bucket_list.description
        data["owner_email"] = invite.bucket_list.owner.email
        data["already_member"] = already_member
        
        return Response(data, status=status.HTTP_200_OK)
    
class BucketListInviteAccept(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_invite(self, token):
        try:
            return BucketListInvite.objects.select_related("bucket_list").get(token=token)
        except BucketListInvite.DoesNotExist:
            raise Http404
        
    def post(self, request, token):
        invite = self.get_invite(token)
        
        serializer = InviteAcceptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not invite.is_active:
            return Response(
                {"detail": "This invite is inactive."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if invite.is_expired:
            return Response(
                {"detail": "This invite has expired."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        existing_membership = BucketListMembership.objects.filter(
            bucket_list=invite.bucket_list,
            user=request.user,
        ).first()
        
        if existing_membership:
            return Response(
                {"detail": "You are already a member of this bucket list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        membership = BucketListMembership.objects.create(
            bucket_list=invite.bucket_list,
            user=request.user,
            role=invite.role,
        )
        
        return Response(
            {
                "detail": "Invite accepted successfully.",
                "bucket_list_id": invite.bucket_list.id,
                "membership_id": membership.id,
                "role": membership.role,
            },
            status=status.HTTP_201_CREATED
        )
        
class BucketListMembershipDetail(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_bucket_list(self, bucket_list_id, user):
        try:
            return BucketList.objects.get(
                pk=bucket_list_id,
                memberships__user=user,
            )
        except BucketList.DoesNotExist:
            raise Http404
        
    def get_membership(self, bucket_list, membership_id):
        try:
            return BucketListMembership.objects.select_related("user", "bucket_list").get(
                pk=membership_id,
                bucket_list=bucket_list,
            )
        except BucketListMembership.DoesNotExist:
            raise Http404
        
    def is_owner(self, bucket_list, user):
        return bucket_list.owner == user
    
    def put(self, request, bucket_list_id, membership_id):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        
        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can update member roles."},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        membership = self.get_membership(bucket_list, membership_id)
        
        if membership.user == request.user:
            return Response(
                {"detail": "Owners cannot change their own membership role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        serializer = BucketListMembershipUpdateSerializer(
            membership,
            data=request.data,
            partial=True,
        )
        
        if serializer.is_valid():
            serializer.save()
            
            response_serializer = BucketListMembershipSerializer(
                membership,
                context={"request": request},
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK,
            )
            
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )
        
    def delete(self, request, bucket_list_id, membership_id):
        bucket_list = self.get_bucket_list(bucket_list_id, request.user)
        membership = self.get_membership(bucket_list, membership_id)
    
        is_owner = self.is_owner(bucket_list, request.user)
        is_self = membership.user == request.user
    
        if membership.user == bucket_list.owner:
            return Response(
                {"detail": "The owner cannot be removed from the bucket list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
        if not is_owner and not is_self:
            return Response(
                {"detail": "You do not have permission to remove this member."},
                status=status.HTTP_403_FORBIDDEN,
            )
    
        membership.delete()
    
        if is_self:
            return Response(
                {"detail": "You have left the bucket list successfully."},
                status=status.HTTP_200_OK,
            )
    
        return Response(
            {"detail": "Member removed successfully."},
            status=status.HTTP_200_OK,
        )