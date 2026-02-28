from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.http import Http404
from .models import Bucket
from .serializers import BucketSerializer
from users.models import User

# Create your views here.

class BucketList(APIView):
    permission_classes = [permissions.IsAuthenticated] #Different user types?
    
    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise Http404
        
    def get(self, request, pk):
        """
        Retrieve a list of all buckets connected to a User
        """
        user = self.get_object(pk)
        
        if request.user != user:
            return Response(
                {"detail": "You do not have permission to view these Bucket Lists"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        buckets = user.owned_buckets.all()
        serializer = BucketSerializer(buckets, many=True)
        return Response(serializer.data)
    
    def post(self, request, pk):
        user = self.get_object(pk)
        
        if request.user != user:
            return Response(
                {"detail": "You do not have permission to create a Bucket List"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BucketSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=user)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
                )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
            )
        
    def put(self, request, pk):
        
        bucket = self.get_object(pk)
        
        if request.user != bucket.user:
            return Response(
                {'detail': "You don't have permission to edit this bucket list"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = BucketSerializer(
            instance=bucket,
            data=request.data,
            partial=True
            )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
            )
        
    def delete(self, request, pk):
        bucket = self.get_object(pk)
        if request.user != bucket.user:
            return Response(
                {"detail": "You don't have permission to delete this List."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        bucket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)