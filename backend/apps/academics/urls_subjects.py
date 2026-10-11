from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SubjectViewSet, TeachingAssignmentViewSet

router = DefaultRouter()
router.register(r'assignments', TeachingAssignmentViewSet, basename='teaching-assignment')
router.register(r'', SubjectViewSet, basename='subject')

urlpatterns = [
    path('', include(router.urls)),
]
