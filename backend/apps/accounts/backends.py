from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from apps.accounts.utils import normalize_phone


class EmailOrPhoneBackend(ModelBackend):
    """Allows login with either an email address or a Kenyan phone number."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        identifier = (
            username
            or kwargs.get("email")
            or kwargs.get("phone")
            or kwargs.get("identifier")
        )
        if not identifier or password is None:
            return None
        identifier = str(identifier).strip()
        phone = normalize_phone(identifier)
        query = Q(email__iexact=identifier)
        if phone:
            query |= Q(phone=phone)
        user = User.objects.filter(query).first()
        if user is None:
            # Mitigate user-enumeration timing differences.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
