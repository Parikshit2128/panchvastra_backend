from rest_framework import serializers


# The value is what is stored and sent over the API; the label is what the
# Help Desk dropdown shows. Kept here, next to the serializers that validate
# against it, so a category can't be added to one and forgotten in the other.
SUPPORT_CATEGORY_CHOICES = [
    ("ORDER_SUPPORT", "Order Support"),
    ("SIZE_PRODUCT", "Size & Product Help"),
    ("COLLABORATION", "Collaborations & Bulk Orders"),
    ("PAYMENT", "Payment Issue"),
    ("WEBSITE", "Website Issue"),
    ("OTHER", "Other"),
]

SUPPORT_CATEGORY_LABELS = dict(SUPPORT_CATEGORY_CHOICES)

SUPPORT_STATUS_CHOICES = ["OPEN", "IN_PROGRESS", "RESOLVED"]


class CreateSupportQuerySerializer(serializers.Serializer):
    """The Help Desk form. Public, so every field has a hard length cap —
    nothing else stops an anonymous caller posting megabytes of text."""

    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    category = serializers.ChoiceField(choices=SUPPORT_CATEGORY_CHOICES)
    message = serializers.CharField(max_length=2000)


class UpdateSupportQuerySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=SUPPORT_STATUS_CHOICES)
