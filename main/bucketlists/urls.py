from django.urls import path
from .views import (
    BucketListList,
    BucketListDetail,
    BucketListItemListCreate,
    BucketListItemDetail,
    ItemVoteAction,
    BucketListInviteManage,
    BucketListInviteDetail,
    BucketListInviteAccept,
    BucketListMembershipDetail,
)

urlpatterns = [
    path("bucketlists/", BucketListList.as_view(), name="bucketlist-list"),
    path("bucketlists/<int:pk>/", BucketListDetail.as_view(), name="bucketlist-detail"),
    
    path(
        "bucketlists/<int:bucket_list_id>/items/",
        BucketListItemListCreate.as_view(),
        name="bucketlist-item-list-create",
        ),
    path(
        "items/<int:pk>/",
        BucketListItemDetail.as_view(),
        name="bucketlist-item-detail",
    ),
    path(
        "items/<int:pk>/vote/",
        ItemVoteAction.as_view(),
        name="item-vote",
    ),
    path(
        "bucketlists/<int:bucket_list_id>/invites/<str:role>/",
        BucketListInviteManage.as_view(),
        name="bucketlist-invite-manage",
    ),
    path(
        "invites/<str:token>/",
        BucketListInviteDetail.as_view(),
        name="bucketlist-invite-detail",
    ),
    path(
        "invites/<str:token>/accept/",
        BucketListInviteAccept.as_view(),
        name="bucketlist-invite-accept",
    ),
    path(
    "bucketlists/<int:bucket_list_id>/members/<int:membership_id>/",
    BucketListMembershipDetail.as_view(),
    name="bucketlist-membership-detail",
    ),
]