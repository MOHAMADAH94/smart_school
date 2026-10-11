from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.grades.gradebook import build_student_gradebook
from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import AcademicTerm, Assessment, Grade
from .serializers import (
    AcademicTermSerializer,
    AssessmentSerializer,
    GradeReportSerializer,
    GradeSerializer,
)

MANAGER_ROLES = {Role.SUPER_ADMIN, Role.SCHOOL_OWNER, Role.SCHOOL_ADMIN}


def teacher_assignment_q(teacher) -> Q:
    """Match only exact classroom+subject pairs assigned to the teacher."""
    q = Q()
    for a in teacher.assignments.all():
        q |= Q(classroom_id=a.classroom_id, subject_id=a.subject_id)
    return q


def teacher_grade_assignment_q(teacher) -> Q:
    q = Q()
    for a in teacher.assignments.all():
        q |= Q(
            assessment__classroom_id=a.classroom_id,
            assessment__subject_id=a.subject_id,
        )
    return q


def require_manager(request):
    membership = getattr(request, 'membership', None)
    if not membership or membership.role not in MANAGER_ROLES:
        raise PermissionDenied('هذا الإجراء متاح لإدارة المدرسة فقط.')


class BulkGradeSerializer(serializers.Serializer):
    assessment_id = serializers.IntegerField()
    records = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate(self, attrs):
        request = self.context['request']
        school = request.school
        try:
            assessment = Assessment.objects.get(id=attrs['assessment_id'], school=school)
        except Assessment.DoesNotExist as exc:
            raise serializers.ValidationError({'assessment_id': 'التقييم غير موجود.'}) from exc

        membership = getattr(request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=school, user=request.user).first()
            allowed = (
                teacher
                and teacher.assignments.filter(
                    classroom_id=assessment.classroom_id,
                    subject_id=assessment.subject_id,
                ).exists()
            )
            if not allowed:
                raise serializers.ValidationError(
                    {'assessment_id': 'التقييم خارج نطاق فصلك ومادتك.'}
                )
        attrs['assessment'] = assessment
        return attrs

    def create(self, validated_data):
        school = self.context['request'].school
        assessment = validated_data['assessment']
        results = []
        for item in validated_data['records']:
            student_id = item.get('student_id')
            score = item.get('score')
            if student_id is None or score in (None, ''):
                continue
            from apps.students.models import Student

            student = Student.objects.filter(
                id=student_id,
                school=school,
                classroom_id=assessment.classroom_id,
            ).first()
            if not student:
                continue
            try:
                score_val = float(score)
            except (TypeError, ValueError):
                continue
            if score_val > float(assessment.max_score):
                continue
            obj, _ = Grade.objects.update_or_create(
                school=school,
                student=student,
                assessment=assessment,
                defaults={'score': score_val, 'notes': item.get('notes', '') or ''},
            )
            results.append(obj)
            try:
                from apps.notifications.events import on_grade_published

                subject_name = getattr(assessment.subject, 'name', 'مادة')
                on_grade_published(
                    school=school,
                    student=student,
                    subject_name=subject_name,
                    assessment_name=getattr(assessment, 'name', ''),
                )
            except Exception:
                pass
        return results


class AcademicTermViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = AcademicTermSerializer
    queryset = AcademicTerm.objects.all()
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'grades'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.GRADES_VIEW
        else:
            self.required_permission = Permission.GRADES_MANAGE
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        require_manager(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        require_manager(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        require_manager(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        require_manager(request)
        return super().destroy(request, *args, **kwargs)


class AssessmentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = AssessmentSerializer
    queryset = Assessment.objects.select_related('subject', 'classroom', 'term')
    filterset_fields = ('subject', 'classroom', 'term', 'assessment_type')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'grades'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.GRADES_VIEW
        else:
            self.required_permission = Permission.GRADES_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        membership = getattr(self.request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=self.request.user).first()
            if not teacher:
                return qs.none()
            q = teacher_assignment_q(teacher)
            return qs.filter(q) if q else qs.none()
        return qs

    def create(self, request, *args, **kwargs):
        require_manager(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        require_manager(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        require_manager(request)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        require_manager(request)
        return super().destroy(request, *args, **kwargs)


class GradeViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = GradeSerializer
    queryset = Grade.objects.select_related('student', 'assessment', 'assessment__subject')
    filterset_fields = (
        'student',
        'assessment',
        'assessment__subject',
        'assessment__classroom',
        'assessment__term',
    )
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'grades'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'report', 'gradebook'):
            self.required_permission = Permission.GRADES_VIEW
        else:
            self.required_permission = Permission.GRADES_MANAGE
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        membership = getattr(self.request, 'membership', None)
        if membership and membership.role == Role.TEACHER:
            from apps.teachers.models import Teacher

            teacher = Teacher.objects.filter(school=membership.school, user=self.request.user).first()
            if not teacher:
                return qs.none()
            q = teacher_grade_assignment_q(teacher)
            return qs.filter(q) if q else qs.none()
        if membership and membership.role == Role.PARENT:
            return qs.filter(student__parent_links__parent__user=self.request.user).distinct()
        return qs

    @action(detail=False, methods=['get'])
    def report(self, request):
        qs = self.filter_queryset(self.get_queryset())
        data = GradeReportSerializer(qs, context={'request': request}).data
        return Response(data)

    @action(detail=False, methods=['get'])
    def gradebook(self, request):
        """Subject × assessment matrix for a student (same layout as parent portal)."""
        from apps.students.models import Student
        from apps.teachers.models import Teacher

        school = request.school
        membership = getattr(request, 'membership', None)
        student_id = request.query_params.get('student')
        if not student_id:
            raise ValidationError({'student': 'معرّف الطالب مطلوب.'})

        student = Student.objects.filter(school=school, id=student_id).select_related('classroom').first()
        if not student:
            raise ValidationError({'student': 'الطالب غير موجود.'})

        role = membership.role if membership else None
        if role == Role.PARENT:
            linked = student.parent_links.filter(parent__user=request.user).exists()
            if not linked:
                raise PermissionDenied('غير مصرح بعرض درجات هذا الطالب.')
        elif role == Role.TEACHER:
            teacher = Teacher.objects.filter(school=school, user=request.user).first()
            if not teacher or not student.classroom_id:
                raise PermissionDenied('غير مصرح بعرض درجات هذا الطالب.')
            if not teacher.assignments.filter(classroom_id=student.classroom_id).exists():
                raise PermissionDenied('هذا الطالب خارج فصولك المسندة.')
        elif role not in MANAGER_ROLES and role != Role.SUPER_ADMIN:
            raise PermissionDenied('غير مصرح.')

        book = build_student_gradebook(student)
        return Response(
            {
                'student': {
                    'id': student.id,
                    'full_name': student.full_name,
                    'student_code': student.student_code,
                    'classroom_id': student.classroom_id,
                    'classroom_name': student.classroom.name if student.classroom_id else None,
                },
                'gradebook': book,
            }
        )

    @action(detail=False, methods=['post'], url_path='bulk')
    def bulk(self, request):
        serializer = BulkGradeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        records = serializer.save()
        return Response(GradeSerializer(records, many=True).data, status=status.HTTP_200_OK)
