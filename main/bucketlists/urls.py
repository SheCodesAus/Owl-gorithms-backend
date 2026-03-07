from django.urls import path
from .views import BucketListList, BucketListDetail, BucketListItemListCreate, BucketListItemDetail

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
]