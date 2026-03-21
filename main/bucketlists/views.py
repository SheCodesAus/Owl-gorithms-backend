from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .notification_services import notify_item_added, notify_item_status_changed

from .models import BucketList, BucketListMembership, BucketListItem, ItemVote, BucketListInvite, Notification
from .serializers import BucketListSerializer, BucketListItemSerializer, ItemVoteSerializer, BucketListInviteSerializer, InviteAcceptSerializer, BucketListMembershipSerializer, BucketListMembershipUpdateSerializer, NotificationSerializer, BucketListFreezeSerializer

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
    GET  — public lists: anyone (authenticated or not)
           private lists: members only
    PUT  — owner only
    DELETE — owner only
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_object_for_read(self, pk, user):
        """
        Returns the bucket list if the user is allowed to read it.
        - Public list: always allowed.
        - Private list: must be a member.
        """
        try:
            bucket_list = BucketList.objects.get(pk=pk)
        except BucketList.DoesNotExist:
            raise Http404

        if bucket_list.is_public:
            return bucket_list

        # Private — must be authenticated and a member
        if not user or not user.is_authenticated:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This list is private. You must be a member to view it.")

        if not bucket_list.memberships.filter(user=user).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This list is private. You must be a member to view it.")

        return bucket_list

    def get_object_for_write(self, pk, user):
        """Write operations always require membership."""
        try:
            return BucketList.objects.get(pk=pk, memberships__user=user)
        except BucketList.DoesNotExist:
            raise Http404

    def is_owner(self, bucket_list, user):
        return bucket_list.owner == user

    def get(self, request, pk):
        bucket_list = self.get_object_for_read(pk, request.user)
        serializer = BucketListSerializer(bucket_list, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        bucket_list = self.get_object_for_write(pk, request.user)

        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can update this bucket list."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BucketListSerializer(
            bucket_list,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        bucket_list = self.get_object_for_write(pk, request.user)

        if not self.is_owner(bucket_list, request.user):
            return Response(
                {"detail": "Only the owner can delete this bucket list."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bucket_list.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BucketListItemListCreate(APIView):
    """
    GET  — public lists: anyone can read items
           private lists: members only
    POST — members with editor/owner role only (list must not be frozen)
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_bucket_list_for_read(self, bucket_list_id, user):
        try:
            bucket_list = BucketList.objects.get(pk=bucket_list_id)
        except BucketList.DoesNotExist:
            raise Http404

        if bucket_list.is_public:
            return bucket_list

        if not user or not user.is_authenticated:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This list is private.")

        if not bucket_list.memberships.filter(user=user).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("This list is private.")

        return bucket_list

    def get_bucket_list_for_write(self, bucket_list_id, user):
        try:
            return BucketList.objects.get(
                pk=bucket_list_id,
                memberships__user=user,
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
        bucket_list = self.get_bucket_list_for_read(bucket_list_id, request.user)
        items = bucket_list.items.all()
        serializer = BucketListItemSerializer(
            items, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, bucket_list_id):
        # Write always requires authentication + membership
        bucket_list = self.get_bucket_list_for_write(bucket_list_id, request.user)
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
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BucketListItemSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            item = serializer.save(
                bucket_list=bucket_list,
                created_by=request.user,
            )
            notify_item_added(item, actor=request.user)
            response_serializer = BucketListItemSerializer(
                item, context={"request": request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        old_status = item.status  # capture BEFORE save
            
        serializer = BucketListItemSerializer(
            item,
            data=data,
            partial=True,
            context={"request": request},
        )
        
        if serializer.is_valid():
            updated_item = serializer.save()  # capture return value
            if old_status != updated_item.status and updated_item.status in ("locked_in", "complete"):
                notify_item_status_changed(updated_item, actor=request.user)
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
    """
    Voting requires authentication.
    Public list + allow_viewer_voting=True → any authenticated user can vote.
    Private list → must be a member with appropriate role.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_item(self, pk, user):
        """
        For voting, the item must be on a list the user can access.
        Public list: any authenticated user.
        Private list: must be a member.
        """
        try:
            item = BucketListItem.objects.select_related("bucket_list").get(pk=pk)
        except BucketListItem.DoesNotExist:
            raise Http404

        bucket_list = item.bucket_list

        if bucket_list.is_public:
            return item

        # Private — must be a member
        if not bucket_list.memberships.filter(user=user).exists():
            raise Http404

        return item

    def get_membership(self, bucket_list, user):
        """Returns membership or None for public list non-members."""
        try:
            return BucketListMembership.objects.get(
                bucket_list=bucket_list,
                user=user,
            )
        except BucketListMembership.DoesNotExist:
            return None

    def can_vote(self, bucket_list, membership):
        if bucket_list.is_frozen:
            return False

        # Public list with viewer voting enabled — any authenticated user can vote
        if bucket_list.is_public and bucket_list.allow_viewer_voting:
            return True

        # Must be a member with the right role
        if not membership:
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
                status=status.HTTP_403_FORBIDDEN,
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
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            vote = ItemVote.objects.get(item=item, user=request.user)
        except ItemVote.DoesNotExist:
            return Response(
                {"detail": "You do not have a vote on this item."},
                status=status.HTTP_404_NOT_FOUND,
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
        
class NotificationList(APIView):
    """
    GET  /api/notifications/
    Returns paginated notifications for the current user, unread first.
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_dismissed=False,
            created_at__gte=timezone.now() - timedelta(days=30),
        ).select_related("actor", "bucket_list", "item")
 
        serializer = NotificationSerializer(
            notifications,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

 
class NotificationUnreadCount(APIView):
    """
    GET  /api/notifications/unread-count/
    Lightweight endpoint polled every 30s by the frontend.
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)
 
 
class NotificationMarkRead(APIView):
    """
    POST /api/notifications/read/
    Body: { "id": 5 }        → mark one as read
    Body: { "all": true }    → mark all as read
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def post(self, request):
        mark_all = request.data.get("all", False)
        dismiss = request.data.get("dismiss", False)
        notification_id = request.data.get("id")
 
        # ── Mark all as read ──────────────────────────────────────────────
        if mark_all and not dismiss:
            Notification.objects.filter(
                recipient=request.user,
                is_read=False,
            ).update(is_read=True)
            return Response(
                {"detail": "All notifications marked as read."},
                status=status.HTTP_200_OK,
            )
 
        # ── Dismiss all ───────────────────────────────────────────────────
        if mark_all and dismiss:
            Notification.objects.filter(
                recipient=request.user,
                is_dismissed=False,
            ).update(is_dismissed=True)
            return Response(
                {"detail": "All notifications dismissed."},
                status=status.HTTP_200_OK,
            )
 
        # ── Single notification action ────────────────────────────────────
        if not notification_id:
            return Response(
                {"detail": "Provide 'id', or 'all: true'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        try:
            notification = Notification.objects.get(
                pk=notification_id,
                recipient=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
 
        if dismiss:
            notification.is_dismissed = True
            notification.save(update_fields=["is_dismissed"])
            return Response(
                {"detail": "Notification dismissed."},
                status=status.HTTP_200_OK,
            )
 
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(
            {"detail": "Notification marked as read."},
            status=status.HTTP_200_OK,
        )

class BucketListFreezeToggle(APIView):
    """
    PUT /api/bucketlists/:id/freeze/
    Owner only. Manually freeze or unfreeze a bucket list.
 
    Body: { "is_frozen": true }  or  { "is_frozen": false }
 
    Freezing:
      - Sets is_frozen = True
      - Notifies all members
 
    Unfreezing:
      - Sets is_frozen = False
      - Clears decision_deadline so the management command
        won't auto-refreeze on the next run
    """
    permission_classes = [permissions.IsAuthenticated]
 
    def get_bucket_list(self, pk, user):
        try:
            return BucketList.objects.get(pk=pk, memberships__user=user)
        except BucketList.DoesNotExist:
            raise Http404
 
    def put(self, request, pk):
        bucket_list = self.get_bucket_list(pk, request.user)
 
        if bucket_list.owner != request.user:
            return Response(
                {"detail": "Only the owner can freeze or unfreeze this list."},
                status=status.HTTP_403_FORBIDDEN,
            )
 
        serializer = BucketListFreezeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
 
        freeze = serializer.validated_data["is_frozen"]
        already_in_state = bucket_list.is_frozen == freeze
 
        if already_in_state:
            return Response(
                {
                    "detail": f"List is already {'frozen' if freeze else 'unfrozen'}.",
                    "is_frozen": bucket_list.is_frozen,
                },
                status=status.HTTP_200_OK,
            )
 
        bucket_list.is_frozen = freeze
 
        if not freeze:
            # Unfreezing — clear deadline so management command
            # won't auto-refreeze on next run
            bucket_list.decision_deadline = None
 
        bucket_list.save(update_fields=["is_frozen", "decision_deadline"])
 
        # Notify all members when freezing
        if freeze:
            from .notification_services import notify_list_frozen
            notify_list_frozen(bucket_list)
 
        response_serializer = BucketListSerializer(
            bucket_list, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)
