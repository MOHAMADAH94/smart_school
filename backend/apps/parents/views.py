from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.grades.gradebook import build_student_gradebook
from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import Parent, StudentParent
from .serializers import ParentSerializer, StudentParentSerializer


class ParentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ParentSerializer
    queryset = Parent.objects.select_related('user')
    search_fields = ('name', 'phone', 'email', 'user__username')
    filterset_fields = ('relationship',)
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'parents'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'my_children'):
            self.required_permission = Permission.PARENTS_VIEW
        else:
            self.required_permission = Permission.PARENTS_MANAGE
        if self.action == 'my_children':
            self.required_permission = Permission.STUDENTS_VIEW
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='create-login')
    def create_login(self, request, pk=None):
        """Create or reset login credentials for an existing parent profile."""
        parent = self.get_object()
        serializer = ParentSerializer(
            parent,
            data={
                'username': request.data.get('username', ''),
                'password': request.data.get('password', ''),
            },
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ParentSerializer(parent, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='my-children')
    def my_children(self, request):
        """Children linked to the current parent user, with performance summary."""
        school = request.school
        parent = Parent.objects.filter(school=school, user=request.user).first()
        if parent is None:
            # Fallback: membership role PARENT without linked profile
            return Response({'parent': None, 'children': []})

        links = (
            StudentParent.objects.filter(school=school, parent=parent)
            .select_related('student', 'student__classroom')
            .prefetch_related('student__attendance_records', 'student__grades', 'student__fees', 'student__payments')
        )
        today = timezone.localdate()
        children = []
        for link in links:
            student = link.student
            attendance_qs = student.attendance_records.all()
            present = attendance_qs.filter(status='PRESENT').count()
            absent = attendance_qs.filter(status='ABSENT').count()
            late = attendance_qs.filter(status='LATE').count()
            avg_grade = student.grades.aggregate(avg=Avg('score'))['avg']
            if avg_grade is not None:
                avg_grade = round(float(avg_grade), 2)
            total_fees = student.fees.aggregate(s=Sum('amount'))['s'] or 0
            paid = student.payments.aggregate(s=Sum('amount'))['s'] or 0
            transport = student.transport_assignments.filter(status='ACTIVE').select_related(
                'bus', 'route'
            ).first()
            attendance_rows = list(
                student.attendance_records.order_by('-date')[:40].values(
                    'id', 'date', 'status', 'notes'
                )
            )
            fees = [
                {
                    'id': f.id,
                    'title': f.title,
                    'amount': f.amount,
                    'paid_amount': getattr(f, 'paid_amount', None),
                    'remaining_amount': getattr(f, 'remaining_amount', None),
                    'academic_year': f.academic_year,
                    'due_date': f.due_date,
                }
                for f in student.fees.all()[:30]
            ]
            payments = list(
                student.payments.order_by('-payment_date')[:20].values(
                    'id', 'amount', 'payment_date', 'method', 'reference'
                )
            )
            children.append(
                {
                    'id': student.id,
                    'student_code': student.student_code,
                    'full_name': student.full_name,
                    'classroom_name': student.classroom.name if student.classroom_id else None,
                    'status': student.status,
                    'relationship': link.relationship,
                    'today_status': (
                        student.attendance_records.filter(date=today).values_list('status', flat=True).first()
                    ),
                    'attendance_summary': {
                        'present': present,
                        'absent': absent,
                        'late': late,
                        'total': attendance_qs.count(),
                    },
                    'attendance': attendance_rows,
                    'average_grade': avg_grade,
                    'gradebook': build_student_gradebook(student),
                    'finance': {
                        'total_fees': total_fees,
                        'paid': paid,
                        'remaining': total_fees - paid,
                    },
                    'fees': fees,
                    'payments': payments,
                    'transport': (
                        {
                            'bus_number': transport.bus.bus_number,
                            'route_name': transport.route.name,
                            'pickup_location': transport.pickup_location,
                            'dropoff_location': transport.dropoff_location,
                            'monthly_fee': transport.monthly_fee,
                            'status': transport.status,
                        }
                        if transport
                        else None
                    ),
                }
            )

        return Response(
            {
                'parent': ParentSerializer(parent).data,
                'children': children,
            }
        )


class StudentParentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = StudentParentSerializer
    queryset = StudentParent.objects.select_related('student', 'parent')
    filterset_fields = ('student', 'parent', 'relationship')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'parents'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.PARENTS_VIEW
        else:
            self.required_permission = Permission.PARENTS_MANAGE
        return super().get_permissions()
