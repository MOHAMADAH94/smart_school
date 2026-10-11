from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcademicTermViewSet, AssessmentViewSet, GradeViewSet

router = DefaultRouter()
router.register(r'terms', AcademicTermViewSet, basename='term')
router.register(r'assessments', AssessmentViewSet, basename='assessment')
router.register(r'', GradeViewSet, basename='grade')

urlpatterns = [
    path('', include(router.urls)),
]
