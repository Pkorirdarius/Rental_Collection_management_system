from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts import twofa
from apps.accounts.models import User
from apps.accounts.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    TwoFACodeSerializer,
    TwoFADisableSerializer,
    TwoFAVerifySerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from apps.core.audit import audit
from apps.core.models import AuditLog
from apps.core.permissions import IsAdmin

CHALLENGE_SALT = "rent-manager-2fa"
CHALLENGE_MAX_AGE = 300


def _tokens_for(user, request):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["org"] = str(user.organization_id or "")
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


def _challenge_for(user) -> str:
    return signing.dumps({"uid": str(user.pk)}, salt=CHALLENGE_SALT)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            audit(AuditLog.Action.LOGIN_FAILED, changes={"identifier": serializer.validated_data["identifier"]})
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if user.locked_until:
            from django.utils import timezone

            if user.locked_until > timezone.now():
                return Response({"detail": "Account temporarily locked."}, status=423)

        user.last_login_ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
        user.failed_login_count = 0
        user.save(update_fields=["last_login_ip", "failed_login_count", "updated_at"])
        audit(AuditLog.Action.LOGIN, actor=user, organization=user.organization)

        if user.totp_enabled:
            return Response({"mfa_required": True, "challenge": _challenge_for(user)})

        return Response(_tokens_for(user, request))


class TwoFAVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        serializer = TwoFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = signing.loads(
                serializer.validated_data["challenge"],
                salt=CHALLENGE_SALT,
                max_age=CHALLENGE_MAX_AGE,
            )
        except signing.BadSignature:
            return Response({"detail": "Invalid or expired challenge."}, status=400)
        user = User.objects.filter(pk=payload.get("uid"), is_active=True).first()
        if user is None:
            return Response({"detail": "Invalid challenge."}, status=400)

        code = serializer.validated_data["code"]
        if not twofa.verify_code(user.totp_secret, code):
            if not twofa.consume_backup_code(user, code):
                audit(AuditLog.Action.LOGIN_FAILED, actor=user, changes={"reason": "bad_totp"})
                return Response({"detail": "Invalid authentication code."}, status=400)
        audit(AuditLog.Action.LOGIN, actor=user, organization=user.organization, changes={"mfa": True})
        return Response(_tokens_for(user, request))


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"detail": "refresh is required."}, status=400)
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=400)
        audit(AuditLog.Action.LOGOUT, actor=request.user, organization=request.user.organization)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class TwoFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_admin:
            return Response({"detail": "2FA is available to admins only."}, status=403)
        secret = request.user.totp_secret or twofa.generate_secret()
        if not request.user.totp_secret:
            request.user.totp_secret = secret
            request.user.save(update_fields=["totp_secret", "updated_at"])
        uri = twofa.provisioning_uri(secret, request.user.email)
        return Response(
            {
                "secret": secret,
                "otpauth_url": uri,
                "qr": twofa.qr_data_uri(uri),
                "enabled": request.user.totp_enabled,
            }
        )


class TwoFAEnableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFACodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.totp_secret:
            return Response({"detail": "Run setup first."}, status=400)
        if not twofa.verify_code(request.user.totp_secret, serializer.validated_data["code"]):
            return Response({"detail": "Invalid authentication code."}, status=400)
        codes = twofa.generate_backup_codes()
        request.user.totp_enabled = True
        request.user.backup_codes = twofa.dump_backup_codes(codes)
        request.user.save(update_fields=["totp_enabled", "backup_codes", "updated_at"])
        audit(AuditLog.Action.UPDATE, obj=request.user, changes={"totp_enabled": True})
        return Response({"enabled": True, "backup_codes": codes})


class TwoFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFADisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["password"]):
            return Response({"detail": "Password is incorrect."}, status=400)
        request.user.totp_enabled = False
        request.user.totp_secret = ""
        request.user.backup_codes = ""
        request.user.save(update_fields=["totp_enabled", "totp_secret", "backup_codes", "updated_at"])
        audit(AuditLog.Action.UPDATE, obj=request.user, changes={"totp_enabled": False})
        return Response({"enabled": False})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(AuditLog.Action.UPDATE, obj=request.user, changes={"password": "changed"})
        return Response({"detail": "Password updated."})


class UserViewSet(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserCreateSerializer

    def get_queryset(self):
        return User.objects.filter(organization=self.request.user.organization).exclude(
            role=User.Role.TENANT
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def list(self, request, *args, **kwargs):
        return Response(UserSerializer(self.get_queryset(), many=True).data)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    serializer_class = UserUpdateSerializer

    def get_queryset(self):
        return User.objects.filter(organization=self.request.user.organization).exclude(
            role=User.Role.TENANT
        )

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({"detail": "You cannot deactivate your own account."}, status=400)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        audit(AuditLog.Action.DELETE, obj=user, changes={"is_active": False})
        return Response(status=status.HTTP_204_NO_CONTENT)
