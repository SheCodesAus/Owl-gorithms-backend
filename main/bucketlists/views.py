from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.http import Http404
from .models import BucketList, BucketItem
from .serializers import BucketListSerializer, BucketItemSerializer


class BucketListAll(APIView):
    """
    Get all Bucketlists, Create new Bucketlist
    """
    def get(self, request):
        bucketlists = BucketList.objects.filter(is_open=True)
        serializer = BucketListSerializer(bucketlists, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, pk):
        owner = self.get_object(pk)
        
        serializer = BucketListSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=owner)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
        
class BucketListDetail(APIView):
    """
    Single BucketList Detail + Update + Delete
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return BucketList.objects.get(pk=pk)
        except BucketList.DoesNotExist:
            raise Http404
        
    def get(self, request, pk):
        bucketlist = self.get_object(pk)
        serializer = BucketList(bucketlist)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
            )
        
    def put(self, request, pk):
        bucketlist = self.get_object(pk)
        serializer = BucketListSerializer(bucketlist)
        
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
        bucketlist = self.get_object(pk)
        
        if request.user != bucketlist.owner:
            return Response(
                {"detail": "You don't have permission to delete this BucketList."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        bucketlist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)