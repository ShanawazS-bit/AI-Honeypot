from rest_framework import serializers

class MessageSerializer(serializers.Serializer):
    sender = serializers.CharField(required=False)
    text = serializers.CharField()
    timestamp = serializers.FloatField(required=False)

class MetadataSerializer(serializers.Serializer):
    channel = serializers.CharField(required=False)
    language = serializers.CharField(required=False)
    locale = serializers.CharField(required=False)

class ScamInputSerializer(serializers.Serializer):
    sessionId = serializers.CharField()
    message = MessageSerializer()
    conversationHistory = serializers.ListField(
        child=serializers.DictField(),
        required=False, 
        default=list
    )
    metadata = MetadataSerializer(required=False)
