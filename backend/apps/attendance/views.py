from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission
from apps.subscriptions.permissions import RequiresFeature

from .models import Attendance
from .serializers import AttendanceSerializer, BulkAttendanceSerializer


class AttendanceViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    queryset = Attendance.objects.select_related('student')
    filterset_fields = ('date', 'status', 'student', 'student__classroom')
    search_fields = ('student__first_name', 'student__last_name', 'student__student_code')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'attendance'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.ATTENDANCE_VIEW
        else:
            self.required_permission = Permission.ATTENDANCE_MANAGE
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(school=self.get_school(), recorded_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        serializer = BulkAttendanceSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        records = serializer.save()
        return Response(
            AttendanceSerializer(records, many=True).data,
            status=status.HTTP_200_OK,
        )
