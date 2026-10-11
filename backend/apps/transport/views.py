from rest_framework import viewsets

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission
from apps.subscriptions.permissions import RequiresFeature

from .models import Bus, BusDriver, BusRoute, StudentTransport
from .serializers import (
    BusDriverSerializer,
    BusRouteSerializer,
    BusSerializer,
    StudentTransportSerializer,
)


class TransportBase(TenantQuerysetMixin):
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'transport'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.TRANSPORT_VIEW
        else:
            self.required_permission = Permission.TRANSPORT_MANAGE
        return super().get_permissions()


class BusDriverViewSet(TransportBase, viewsets.ModelViewSet):
    serializer_class = BusDriverSerializer
    queryset = BusDriver.objects.all()
    search_fields = ('name', 'phone', 'license_number')
    filterset_fields = ('is_active',)


class BusViewSet(TransportBase, viewsets.ModelViewSet):
    serializer_class = BusSerializer
    queryset = Bus.objects.select_related('driver').prefetch_related('student_assignments')
    search_fields = ('bus_number', 'vehicle_number', 'phone')
    filterset_fields = ('vehicle_type', 'is_active', 'driver')


class BusRouteViewSet(TransportBase, viewsets.ModelViewSet):
    serializer_class = BusRouteSerializer
    queryset = BusRoute.objects.select_related('bus', 'driver').prefetch_related('student_assignments')
    search_fields = ('name', 'start_location', 'end_location', 'stops')
    filterset_fields = ('bus', 'driver', 'is_active')


class StudentTransportViewSet(TransportBase, viewsets.ModelViewSet):
    serializer_class = StudentTransportSerializer
    queryset = StudentTransport.objects.select_related('student', 'bus', 'route')
    search_fields = ('student__first_name', 'student__last_name', 'bus__bus_number', 'route__name')
    filterset_fields = ('status', 'bus', 'route', 'student')

    def perform_create(self, serializer):
        assignment = serializer.save(school=self.get_school())
        try:
            from apps.notifications.events import on_transport_assigned

            bus = assignment.bus
            if bus and assignment.student_id:
                on_transport_assigned(
                    school=self.get_school(),
                    student=assignment.student,
                    bus_number=bus.bus_number,
                )
        except Exception:
            pass

    def perform_update(self, serializer):
        prev_bus_id = serializer.instance.bus_id
        assignment = serializer.save()
        if assignment.bus_id and assignment.bus_id != prev_bus_id:
            try:
                from apps.notifications.events import on_transport_assigned

                on_transport_assigned(
                    school=self.get_school(),
                    student=assignment.student,
                    bus_number=assignment.bus.bus_number,
                )
            except Exception:
                pass
