from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BusDriverViewSet, BusRouteViewSet, BusViewSet, StudentTransportViewSet

router = DefaultRouter()
router.register(r'drivers', BusDriverViewSet, basename='bus-driver')
router.register(r'buses', BusViewSet, basename='bus')
router.register(r'routes', BusRouteViewSet, basename='bus-route')
router.register(r'assignments', StudentTransportViewSet, basename='student-transport')

urlpatterns = [
    path('', include(router.urls)),
]
