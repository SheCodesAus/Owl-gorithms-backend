from django.urls import path
from .views import BucketListList, BucketListDetail

urlpatterns = [
    path("bucketlists/", BucketListList.as_view(), name="bucketlist-list"),
    path("bucketlists/<int:pk>/", BucketListDetail.as_view(), name="bucketlist-detail"),
]