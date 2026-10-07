import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


# The four kinds of choice on the "Build your piece" page. All of them live in
# one custom_options table, told apart by option_type, so admins manage every
# choice through the same endpoint.
CUSTOM_OPTION_TYPES = ["GARMENT", "COLOUR", "SIZE", "PRINT_TYPE"]

CUSTOM_REQUEST_STATUSES = [
    "NEW",
    "IN_REVIEW",
    "APPROVED",
    "IN_PRODUCTION",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED"
]

DESIGN_FILE_MAX_BYTES = 10 * 1024 * 1024

DESIGN_DESCRIPTION_MAX_LENGTH = 300

HEX_CODE_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

COUNTRY_CODE_PATTERN = re.compile(r"^\+\d{1,4}$")

PHONE_NUMBER_PATTERN = re.compile(r"^\d{6,15}$")


def validate_design_file(design_file):
    """PNG / JPG / PDF up to 10 MB, checked by content, not just the name.

    The name and the browser-supplied content type are both trivially faked,
    so an image must actually open as an image and a PDF must start with the
    PDF signature. Returns the file; raises a DRF ValidationError otherwise.
    """

    if design_file.size > DESIGN_FILE_MAX_BYTES:
        raise serializers.ValidationError("File must be 10 MB or smaller.")

    extension = design_file.name.rsplit(".", 1)[-1].lower() if "." in design_file.name else ""

    if extension == "pdf":

        header = design_file.read(5)
        design_file.seek(0)

        if header != b"%PDF-":
            raise serializers.ValidationError("File is not a valid PDF.")

        return design_file

    if extension not in ("png", "jpg", "jpeg"):
        raise serializers.ValidationError("Only PNG, JPG or PDF files are allowed.")

    try:
        serializers.ImageField().run_validation(design_file)
    except (serializers.ValidationError, DjangoValidationError):
        raise serializers.ValidationError("File is not a valid PNG or JPG image.")

    design_file.seek(0)

    return design_file


class CreateCustomRequestSerializer(serializers.Serializer):
    """The customer's "Create my piece" submission (multipart/form-data)."""

    garment_id = serializers.IntegerField()
    colour_id = serializers.IntegerField()
    size_id = serializers.IntegerField()
    print_type_id = serializers.IntegerField()

    design_file = serializers.FileField(required=False, allow_null=True)

    design_description = serializers.CharField(
        max_length=DESIGN_DESCRIPTION_MAX_LENGTH,
        required=False,
        allow_blank=True,
        allow_null=True
    )

    full_name = serializers.CharField(max_length=100)
    phone_country_code = serializers.CharField(max_length=5, default="+91")
    phone_number = serializers.CharField(max_length=15)

    def validate_design_file(self, value):
        if value is None:
            return value
        return validate_design_file(value)

    def validate_phone_country_code(self, value):
        value = value.strip()
        if not COUNTRY_CODE_PATTERN.match(value):
            raise serializers.ValidationError("Enter a country code like +91.")
        return value

    def validate_phone_number(self, value):
        # Spaces and dashes are what people naturally type into a phone
        # field, so they are dropped rather than rejected.
        value = re.sub(r"[\s-]", "", value)
        if not PHONE_NUMBER_PATTERN.match(value):
            raise serializers.ValidationError("Enter a valid phone number (digits only).")
        return value

    def validate(self, attrs):
        # The page offers upload OR a written idea. One of the two is the
        # minimum; sending both is fine.
        description = (attrs.get("design_description") or "").strip()
        attrs["design_description"] = description or None

        if not attrs.get("design_file") and not description:
            raise serializers.ValidationError({
                "design": "Upload a design or describe your idea."
            })

        return attrs


class UpdateCustomRequestSerializer(serializers.Serializer):
    """Admin moves a request along and/or leaves a note on it."""

    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=CUSTOM_REQUEST_STATUSES, required=False)
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        attrs["note"] = (attrs.get("note") or "").strip() or None

        if not attrs.get("status") and not attrs["note"]:
            raise serializers.ValidationError("Send a status, a note, or both.")

        return attrs


class CustomOptionSerializer(serializers.Serializer):
    """Create one choice on the page (admin, multipart/form-data or JSON).

    Which extra fields matter depends on option_type:
      GARMENT     image, description, colour_ids (the colours it comes in)
      COLOUR      hex_code (the swatch)
      PRINT_TYPE  image, description
      SIZE        nothing extra
    """

    option_type = serializers.ChoiceField(choices=CUSTOM_OPTION_TYPES)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    hex_code = serializers.CharField(max_length=7, required=False, allow_blank=True, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)
    colour_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    display_order = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_hex_code(self, value):
        if not value:
            return None
        if not HEX_CODE_PATTERN.match(value):
            raise serializers.ValidationError("Use a colour like #000000.")
        return value.upper()

    def validate(self, attrs):
        option_type = attrs["option_type"]

        if option_type == "COLOUR" and not attrs.get("hex_code"):
            raise serializers.ValidationError({"hex_code": "A colour needs a hex code."})

        if option_type == "GARMENT" and not attrs.get("colour_ids"):
            raise serializers.ValidationError({
                "colour_ids": "Pick at least one colour this garment comes in."
            })

        if option_type != "GARMENT" and attrs.get("colour_ids"):
            raise serializers.ValidationError({
                "colour_ids": "Only a garment has colours."
            })

        return attrs


class UpdateCustomOptionSerializer(serializers.Serializer):
    """Edit one choice. Send only what changes; option_type can't change."""

    id = serializers.IntegerField()
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    hex_code = serializers.CharField(max_length=7, required=False, allow_blank=True, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)
    colour_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    display_order = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    # default=None, not just required=False: in a multipart form DRF reads an
    # OMITTED boolean as False, which would switch an option off whenever an
    # admin edited only its image. None means "not sent, leave it alone".
    is_active = serializers.BooleanField(required=False, allow_null=True, default=None)

    def validate_hex_code(self, value):
        if not value:
            return None
        if not HEX_CODE_PATTERN.match(value):
            raise serializers.ValidationError("Use a colour like #000000.")
        return value.upper()
