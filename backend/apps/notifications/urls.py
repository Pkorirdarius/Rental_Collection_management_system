from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import (
    MessageLogViewSet,
    NotificationViewSet,
    PromiseViewSet,
    ReminderSettingView,
    ReminderViewSet,
)

router = DefaultRouter()
router.register("reminders", ReminderViewSet, basename="reminder")
router.register("promises", PromiseViewSet, basename="promise")
router.register("messages", MessageLogViewSet, basename="message")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("settings/reminders", ReminderSettingView.as_view(), name="reminder-settings"),
    path("", include(router.urls)),
]
