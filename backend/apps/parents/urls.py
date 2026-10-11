from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ParentViewSet, StudentParentViewSet

router = DefaultRouter()
router.register(r'links/student-parents', StudentParentViewSet, basename='student-parent')
router.register(r'', ParentViewSet, basename='parent')

urlpatterns = [
    path('', include(router.urls)),
]
