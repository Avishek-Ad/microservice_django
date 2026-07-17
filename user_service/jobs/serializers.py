from rest_framework import serializers
from .models import PublishedEvent

class PublishedEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishedEvent
        fields = [
            'channel',
            'payload',
            'is_consumed'
        ]
        read_only_fields = ['id', 'is_consumed']