from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.leases.views import LeaseViewSet

router = DefaultRouter()
router.register("leases", LeaseViewSet, basename="lease")

urlpatterns = [path("", include(router.urls))]
