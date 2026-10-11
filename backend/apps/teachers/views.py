from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import Teacher
from .serializers import TeacherSerializer


class TeacherViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TeacherSerializer
    queryset = Teacher.objects.select_related('user')
    search_fields = ('first_name', 'last_name', 'employee_code', 'phone', 'email', 'specialization', 'user__username')
    filterset_fields = ('status',)
    ordering_fields = ('first_name', 'last_name', 'employee_code', 'hire_date')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'teachers'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'my_classes', 'me'):
            self.required_permission = Permission.TEACHERS_VIEW
        else:
            self.required_permission = Permission.TEACHERS_MANAGE
        # Teachers/parents use portal actions with school/students view — not dashboard.
        if self.action in ('my_classes', 'me'):
            self.required_permission = Permission.STUDENTS_VIEW
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='create-login')
    def create_login(self, request, pk=None):
        """Create or reset login credentials for an existing teacher profile."""
        teacher = self.get_object()
        serializer = TeacherSerializer(
            teacher,
            data={
                'username': request.data.get('username', ''),
                'password': request.data.get('password', ''),
            },
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeacherSerializer(teacher, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        teacher = Teacher.objects.filter(school=request.school, user=request.user).first()
        if not teacher:
            return Response({'teacher': None})
        return Response({'teacher': TeacherSerializer(teacher).data})

    @action(detail=False, methods=['get'], url_path='my-classes')
    def my_classes(self, request):
        """Classrooms and subjects assigned to the current teacher user."""
        teacher = Teacher.objects.filter(school=request.school, user=request.user).first()
        if teacher is None and request.membership.role == Role.TEACHER:
            return Response({'teacher': None, 'assignments': [], 'classrooms': []})

        # Owners/admins can pass teacher_id to inspect; teachers use linked profile.
        teacher_id = request.query_params.get('teacher_id')
        if teacher is None and teacher_id:
            teacher = Teacher.objects.filter(school=request.school, id=teacher_id).first()
        if teacher is None:
            return Response({'teacher': None, 'assignments': [], 'classrooms': []})

        assignments = (
            teacher.assignments.select_related('subject', 'classroom', 'classroom__grade_level')
            .all()
        )
        classroom_map = {}
        assignment_rows = []
        for a in assignments:
            assignment_rows.append(
                {
                    'id': a.id,
                    'subject_id': a.subject_id,
                    'subject_name': a.subject.name,
                    'classroom_id': a.classroom_id,
                    'classroom_name': a.classroom.name,
                    'grade_level_name': a.classroom.grade_level.name,
                }
            )
            if a.classroom_id not in classroom_map:
                classroom_map[a.classroom_id] = {
                    'id': a.classroom_id,
                    'name': a.classroom.name,
                    'grade_level_name': a.classroom.grade_level.name,
                    'student_count': a.classroom.students.filter(status='ACTIVE').count(),
                    'subjects': [],
                }
            classroom_map[a.classroom_id]['subjects'].append(
                {'id': a.subject_id, 'name': a.subject.name}
            )

        return Response(
            {
                'teacher': TeacherSerializer(teacher).data,
                'assignments': assignment_rows,
                'classrooms': list(classroom_map.values()),
            }
        )
