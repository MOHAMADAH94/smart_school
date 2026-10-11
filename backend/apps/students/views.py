import django_filters
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import Student
from .serializers import StudentSerializer


class StudentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(method='filter_name')
    gender = django_filters.CharFilter(field_name='gender')
    status = django_filters.CharFilter(field_name='status')
    classroom = django_filters.NumberFilter(field_name='classroom_id')
    grade = django_filters.NumberFilter(field_name='classroom__grade_level_id')
    bus = django_filters.NumberFilter(field_name='transport_assignments__bus_id')
    transport_status = django_filters.CharFilter(field_name='transport_assignments__status')

    class Meta:
        model = Student
        fields = ['student_code', 'gender', 'status', 'classroom', 'grade', 'bus', 'transport_status']

    def filter_name(self, queryset, name, value):
        return queryset.filter(
            Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(father_name__icontains=value)
        )


class StudentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.select_related('classroom', 'classroom__grade_level')
    filterset_class = StudentFilter
    search_fields = (
        'first_name',
        'father_name',
        'last_name',
        'student_code',
        'phone',
    )
    ordering_fields = ('first_name', 'last_name', 'student_code', 'created_at')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'students'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'profile'):
            self.required_permission = Permission.STUDENTS_VIEW
        else:
            self.required_permission = Permission.STUDENTS_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        membership = getattr(self.request, 'membership', None)
        if membership is None:
            return qs.none()

        role = membership.role
        user = self.request.user

        if role == Role.PARENT:
            return qs.filter(parent_links__parent__user=user).distinct()

        if role == Role.STUDENT:
            return qs.filter(user=user)

        if role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=user).first()
            if teacher:
                classroom_ids = teacher.assignments.values_list('classroom_id', flat=True)
                return qs.filter(classroom_id__in=classroom_ids).distinct()
            return qs.none()

        return qs

    @action(detail=True, methods=['get'])
    def profile(self, request, pk=None):
        """Rich student profile payload for tabs."""
        student = self.get_object()
        school = request.school

        parents = [
            {
                'id': link.parent_id,
                'link_id': link.id,
                'name': link.parent.name,
                'phone': link.parent.phone,
                'email': link.parent.email,
                'relationship': link.relationship,
                'is_primary': link.is_primary,
            }
            for link in student.parent_links.select_related('parent')
        ]
        attendance = list(
            student.attendance_records.order_by('-date')[:30].values(
                'id', 'date', 'status', 'notes'
            )
        )
        grades = [
            {
                'id': g.id,
                'assessment_name': g.assessment.name,
                'subject_name': g.assessment.subject.name,
                'score': g.score,
                'max_score': g.assessment.max_score,
                'term_name': g.assessment.term.name,
            }
            for g in student.grades.select_related(
                'assessment', 'assessment__subject', 'assessment__term'
            ).order_by('-created_at')[:50]
        ]
        transport = student.transport_assignments.select_related('bus', 'route').order_by('-created_at').first()
        fees = [
            {
                'id': f.id,
                'title': f.title,
                'amount': f.amount,
                'paid_amount': f.paid_amount,
                'remaining_amount': f.remaining_amount,
                'academic_year': f.academic_year,
            }
            for f in student.fees.prefetch_related('payments')
        ]
        payments = list(
            student.payments.order_by('-payment_date')[:20].values(
                'id', 'amount', 'payment_date', 'method', 'reference'
            )
        )

        return Response(
            {
                'student': StudentSerializer(student).data,
                'parents': parents,
                'attendance': attendance,
                'grades': grades,
                'transport': (
                    {
                        'id': transport.id,
                        'bus': transport.bus_id,
                        'bus_number': transport.bus.bus_number,
                        'route': transport.route_id,
                        'route_name': transport.route.name,
                        'pickup_location': transport.pickup_location,
                        'dropoff_location': transport.dropoff_location,
                        'monthly_fee': transport.monthly_fee,
                        'status': transport.status,
                        'notes': transport.notes,
                    }
                    if transport
                    else None
                ),
                'fees': fees,
                'payments': payments,
            }
        )
