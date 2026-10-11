from django.db.models import Count
from rest_framework import viewsets

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import Classroom, GradeLevel, Subject, TeachingAssignment
from .serializers import (
    ClassroomSerializer,
    GradeLevelSerializer,
    SubjectSerializer,
    TeachingAssignmentSerializer,
)


class GradeLevelViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = GradeLevelSerializer
    queryset = GradeLevel.objects.all()
    search_fields = ('name',)
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'classes'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.CLASSES_VIEW
        else:
            self.required_permission = Permission.CLASSES_MANAGE
        return super().get_permissions()


class ClassroomViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ClassroomSerializer
    queryset = Classroom.objects.select_related('grade_level')
    search_fields = ('name', 'section')
    filterset_fields = ('grade_level',)
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'classes'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.CLASSES_VIEW
        else:
            self.required_permission = Permission.CLASSES_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset().annotate(student_count=Count('students', distinct=True))
        membership = getattr(self.request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=self.request.user).first()
            if not teacher:
                return qs.none()
            classroom_ids = teacher.assignments.values_list('classroom_id', flat=True)
            return qs.filter(id__in=classroom_ids).distinct()
        return qs


class SubjectViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    queryset = Subject.objects.all()
    search_fields = ('name', 'code')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'subjects'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.SUBJECTS_VIEW
        else:
            self.required_permission = Permission.SUBJECTS_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        membership = getattr(self.request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=self.request.user).first()
            if not teacher:
                return qs.none()
            subject_ids = teacher.assignments.values_list('subject_id', flat=True)
            return qs.filter(id__in=subject_ids).distinct()
        return qs


class TeachingAssignmentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TeachingAssignmentSerializer
    queryset = TeachingAssignment.objects.select_related('teacher', 'subject', 'classroom')
    filterset_fields = ('teacher', 'subject', 'classroom')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'subjects'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.SUBJECTS_VIEW
        else:
            self.required_permission = Permission.SUBJECTS_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        membership = getattr(self.request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=self.request.user).first()
            if not teacher:
                return qs.none()
            return qs.filter(teacher=teacher)
        return qs
