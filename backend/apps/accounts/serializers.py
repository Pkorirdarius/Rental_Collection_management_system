from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone",
            "full_name",
            "role",
            "organization",
            "organization_name",
            "totp_enabled",
            "must_change_password",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "role", "organization", "totp_enabled", "date_joined")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "email", "phone", "full_name", "role", "password")

    def validate_role(self, value):
        if value == User.Role.TENANT:
            raise serializers.ValidationError("Create tenants from the tenant endpoint.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        return User.objects.create_user(
            organization=request.user.organization,
            **validated_data,
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("phone", "full_name", "is_active", "role")

    def validate_role(self, value):
        if value == User.Role.TENANT:
            raise serializers.ValidationError("Tenant roles are managed by tenant records.")
        return value


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email address or phone number")
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class TwoFAVerifySerializer(serializers.Serializer):
    challenge = serializers.CharField()
    code = serializers.CharField()


class TwoFACodeSerializer(serializers.Serializer):
    code = serializers.CharField()


class TwoFADisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=10, validators=[validate_password])

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password", "updated_at"])
        return user


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)
