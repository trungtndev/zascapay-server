from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(allow_blank=True, required=False)
    first_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False, default=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, style={'input_type': 'password'})
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True, allow_null=True)

    # New optional profile fields
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False)
    account_type = serializers.CharField(max_length=20, allow_blank=True, required=False)
    store_name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)

    def validate(self, attrs):
        # Prevent admin flags sneaking via serializer context
        incoming = self.context.get('request').data if self.context.get('request') else {}
        if any(flag in incoming for flag in ['is_staff', 'is_superuser']):
            raise serializers.ValidationError('Admin flags are not allowed for this resource.')
        return attrs
