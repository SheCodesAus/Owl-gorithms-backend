from rest_framework import serializers
from lists.models import List

class ListSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = List
        fields = '__all__'
        
    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.image = validated_data.get('image', instance.image)
        instance.is_open = validated_data.get('is_open', instance.is_open)
        instance.category = validated_data.get('category', instance.category)
        instance.has_deadline = validated_data.get('has_deadline', instance.has_deadline)
        instance.deadline = validated_data.get('deadline', instance.deadline)
        instance.save()
        return instance