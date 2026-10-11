from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    TeacherAvailabilityViewSet,
    TimetableEntryViewSet,
    TimetablePeriodViewSet,
    TimetableViewSet,
    WeeklySubjectRequirementViewSet,
)

# Register nested resources before the empty-prefix TimetableViewSet so
# paths like /periods/ are not captured as timetable pk="periods".
router = DefaultRouter()
router.register(r'periods', TimetablePeriodViewSet, basename='timetable-period')
router.register(r'requirements', WeeklySubjectRequirementViewSet, basename='timetable-requirement')
router.register(r'entries', TimetableEntryViewSet, basename='timetable-entry')
router.register(r'availability', TeacherAvailabilityViewSet, basename='teacher-availability')
router.register(r'', TimetableViewSet, basename='timetable')

urlpatterns = [
    path('', include(router.urls)),
]
