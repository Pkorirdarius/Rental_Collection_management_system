from django.urls import path

from apps.accounts.views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RefreshView,
    TwoFADisableView,
    TwoFAEnableView,
    TwoFASetupView,
    TwoFAVerifyView,
    UserDetailView,
    UserViewSet,
)

urlpatterns = [
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("password/change", PasswordChangeView.as_view(), name="auth-password-change"),
    path("2fa/setup", TwoFASetupView.as_view(), name="auth-2fa-setup"),
    path("2fa/enable", TwoFAEnableView.as_view(), name="auth-2fa-enable"),
    path("2fa/disable", TwoFADisableView.as_view(), name="auth-2fa-disable"),
    path("2fa/verify", TwoFAVerifyView.as_view(), name="auth-2fa-verify"),
    path("users", UserViewSet.as_view(), name="auth-users"),
    path("users/<uuid:pk>", UserDetailView.as_view(), name="auth-user-detail"),
]
