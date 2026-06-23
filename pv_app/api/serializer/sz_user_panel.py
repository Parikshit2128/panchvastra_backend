from rest_framework import serializers


class CreateCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False, default=True)


class UpdateCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    image_url = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)