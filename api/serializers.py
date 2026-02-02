from rest_framework import serializers

class HoneypotRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
