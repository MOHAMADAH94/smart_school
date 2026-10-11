from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClassroomViewSet, GradeLevelViewSet, SubjectViewSet, TeachingAssignmentViewSet

classes_router = DefaultRouter()
classes_router.register(r'grades', GradeLevelViewSet, basename='grade-level')
classes_router.register(r'', ClassroomViewSet, basename='classroom')

subjects_router = DefaultRouter()
subjects_router.register(r'', SubjectViewSet, basename='subject')
subjects_router.register(r'assignments/teaching', TeachingAssignmentViewSet, basename='teaching-assignment')

urlpatterns_classes = [
    path('', include(classes_router.urls)),
]

urlpatterns_subjects = [
    path('', include(subjects_router.urls)),
]
