from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.properties.views import AssignmentViewSet, PropertyViewSet, UnitViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("units", UnitViewSet, basename="unit")
router.register("property-assignments", AssignmentViewSet, basename="property-assignment")

urlpatterns = [path("", include(router.urls))]
