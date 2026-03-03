from django.urls import path
from .views import BucketListAll, BucketListDetail, BucketItemList, BucketItemDetail

urlpatterns = [
    path("bucketlists/", BucketListAll.as_view()),
    path("bucketlists/<int:pk>", BucketListDetail.as_view()),
    
    path("bucketlists/<int:pk>/items/", BucketItemList.as_view()),
    
    path("items/<int:pk>/", BucketItemDetail.as_view()),
]