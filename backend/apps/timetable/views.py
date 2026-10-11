from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.parents.models import Parent, StudentParent
from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature
from apps.teachers.models import Teacher

from .models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableStatus,
    WeeklySubjectRequirement,
)
from .serializers import (
    TeacherAvailabilitySerializer,
    TimetableEntrySerializer,
    TimetablePeriodSerializer,
    TimetableSerializer,
    WeeklySubjectRequirementSerializer,
)
from .services import (
    apply_generated_entries,
    generate_timetable,
    notify_timetable_published,
    publish_timetable,
    validate_timetable,
)


class TimetableViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TimetableSerializer
    queryset = Timetable.objects.all()
    filterset_fields = ('status', 'academic_year')
    search_fields = ('name', 'academic_year')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'timetable'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                entries_count_ann=Count('entries', distinct=True),
                requirements_count_ann=Count('requirements', distinct=True),
            )
            .prefetch_related('periods')
        )

    def get_permissions(self):
        if self.action in (
            'list',
            'retrieve',
            'grid',
            'validate_action',
            'my',
            'for_class',
            'for_teacher',
            'child',
        ):
            self.required_permission = Permission.TIMETABLE_VIEW
        else:
            self.required_permission = Permission.TIMETABLE_MANAGE
        return super().get_permissions()

    def perform_destroy(self, instance):
        if instance.status == TimetableStatus.PUBLISHED:
            raise ValidationError('لا يمكن حذف جدول منشور. أرشفِه أولاً.')
        instance.delete()

    @action(detail=True, methods=['get'])
    def grid(self, request, pk=None):
        timetable = self.get_object()
        classroom_id = request.query_params.get('classroom')
        entries = timetable.entries.select_related(
            'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
        if classroom_id:
            entries = entries.filter(classroom_id=classroom_id)
        return Response(
            {
                'timetable': TimetableSerializer(timetable).data,
                'periods': TimetablePeriodSerializer(timetable.periods.all(), many=True).data,
                'entries': TimetableEntrySerializer(entries, many=True).data,
                'working_days': timetable.get_working_days(),
            }
        )

    @action(detail=True, methods=['get'], url_path='validate')
    def validate_action(self, request, pk=None):
        return Response(validate_timetable(self.get_object()))

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        timetable = self.get_object()
        if timetable.status != TimetableStatus.DRAFT:
            raise ValidationError('التوليد متاح للمسودات فقط.')
        replace = bool(request.data.get('replace_existing'))
        result = generate_timetable(timetable, replace_existing=replace)
        apply = bool(request.data.get('apply'))
        if apply and result.get('proposed'):
            if timetable.entries.exists() and not replace:
                raise ValidationError('يوجد جدول حالي. أكّد الاستبدال بـ replace_existing=true.')
            created = apply_generated_entries(
                timetable, result['proposed'], replace_existing=replace
            )
            result['applied'] = created
            result['validation'] = validate_timetable(timetable)
        return Response(result)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        timetable = self.get_object()
        try:
            publish_timetable(timetable)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        notify_timetable_published(timetable)
        return Response(TimetableSerializer(timetable).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        timetable = self.get_object()
        timetable.status = TimetableStatus.ARCHIVED
        timetable.save(update_fields=['status', 'updated_at'])
        return Response(TimetableSerializer(timetable).data)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Teacher's own published timetable entries."""
        teacher = Teacher.objects.filter(school=request.school, user=request.user).first()
        if not teacher:
            return Response({'entries': [], 'timetable': None})
        timetable = (
            Timetable.objects.filter(school=request.school, status=TimetableStatus.PUBLISHED)
            .order_by('-published_at')
            .first()
        )
        if not timetable:
            return Response({'entries': [], 'timetable': None})
        entries = timetable.entries.filter(
            teaching_assignment__teacher=teacher
        ).select_related(
            'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
        return Response(
            {
                'timetable': TimetableSerializer(timetable).data,
                'entries': TimetableEntrySerializer(entries, many=True).data,
            }
        )

    @action(detail=False, methods=['get'], url_path=r'class/(?P<classroom_id>[0-9]+)')
    def for_class(self, request, classroom_id=None):
        timetable = (
            Timetable.objects.filter(school=request.school, status=TimetableStatus.PUBLISHED)
            .order_by('-published_at')
            .first()
        )
        if not timetable:
            # allow draft preview for managers
            membership = getattr(request, 'membership', None)
            if membership and membership.role in {
                Role.SCHOOL_OWNER,
                Role.SCHOOL_ADMIN,
                Role.SUPER_ADMIN,
            }:
                tid = request.query_params.get('timetable')
                timetable = Timetable.objects.filter(school=request.school, id=tid).first() if tid else None
        if not timetable:
            return Response({'entries': [], 'timetable': None})
        entries = timetable.entries.filter(classroom_id=classroom_id).select_related(
            'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
        return Response(
            {
                'timetable': TimetableSerializer(timetable).data,
                'entries': TimetableEntrySerializer(entries, many=True).data,
                'periods': TimetablePeriodSerializer(timetable.periods.all(), many=True).data,
                'working_days': timetable.get_working_days(),
            }
        )

    @action(detail=False, methods=['get'], url_path=r'child/(?P<student_id>[0-9]+)')
    def child(self, request, student_id=None):
        """Parent view: child's classroom published timetable."""
        membership = getattr(request, 'membership', None)
        if not membership or membership.role != Role.PARENT:
            raise PermissionDenied('متاح لأولياء الأمور فقط.')
        parent = Parent.objects.filter(school=request.school, user=request.user).first()
        if not parent:
            raise PermissionDenied('لا يوجد ملف ولي أمر.')
        link = StudentParent.objects.filter(
            school=request.school, parent=parent, student_id=student_id
        ).select_related('student').first()
        if not link:
            raise PermissionDenied('هذا الطالب غير مرتبط بحسابك.')
        classroom_id = link.student.classroom_id
        if not classroom_id:
            return Response({'entries': [], 'timetable': None, 'student': link.student.full_name})
        timetable = (
            Timetable.objects.filter(school=request.school, status=TimetableStatus.PUBLISHED)
            .order_by('-published_at')
            .first()
        )
        if not timetable:
            return Response({'entries': [], 'timetable': None, 'student': link.student.full_name})
        entries = timetable.entries.filter(classroom_id=classroom_id).select_related(
            'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
        return Response(
            {
                'student': link.student.full_name,
                'classroom_id': classroom_id,
                'classroom_name': link.student.classroom.name if link.student.classroom_id else None,
                'timetable': TimetableSerializer(timetable).data,
                'entries': TimetableEntrySerializer(entries, many=True).data,
                'periods': TimetablePeriodSerializer(timetable.periods.all(), many=True).data,
                'working_days': timetable.get_working_days(),
            }
        )


class TimetablePeriodViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TimetablePeriodSerializer
    queryset = TimetablePeriod.objects.select_related('timetable')
    filterset_fields = ('timetable', 'is_break')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'timetable'
    school_field = 'timetable__school'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.TIMETABLE_VIEW
        else:
            self.required_permission = Permission.TIMETABLE_MANAGE
        return super().get_permissions()

    def perform_create(self, serializer):
        timetable = serializer.validated_data['timetable']
        if timetable.school_id != self.get_school().id:
            raise ValidationError('جدول غير صالح.')
        serializer.save()


class WeeklySubjectRequirementViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = WeeklySubjectRequirementSerializer
    queryset = WeeklySubjectRequirement.objects.select_related(
        'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher', 'timetable'
    )
    filterset_fields = ('timetable', 'classroom', 'subject')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'timetable'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.TIMETABLE_VIEW
        else:
            self.required_permission = Permission.TIMETABLE_MANAGE
        return super().get_permissions()


class TimetableEntryViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TimetableEntrySerializer
    queryset = TimetableEntry.objects.select_related(
        'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher', 'timetable'
    )
    filterset_fields = ('timetable', 'classroom', 'subject', 'day', 'period')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'timetable'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.TIMETABLE_VIEW
        else:
            self.required_permission = Permission.TIMETABLE_MANAGE
        return super().get_permissions()

    def perform_create(self, serializer):
        timetable = serializer.validated_data['timetable']
        if timetable.status != TimetableStatus.DRAFT:
            raise ValidationError('التعديل متاح للمسودات فقط.')
        serializer.save(school=self.get_school())

    def perform_update(self, serializer):
        if serializer.instance.timetable.status != TimetableStatus.DRAFT:
            raise ValidationError('التعديل متاح للمسودات فقط.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.timetable.status != TimetableStatus.DRAFT:
            raise ValidationError('الحذف متاح للمسودات فقط.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        entry = self.get_object()
        if entry.timetable.status != TimetableStatus.DRAFT:
            raise ValidationError('النقل متاح للمسودات فقط.')
        day = request.data.get('day', entry.day)
        period_id = request.data.get('period', entry.period_id)
        period = TimetablePeriod.objects.filter(id=period_id, timetable=entry.timetable).first()
        if not period:
            raise ValidationError('حصة غير صالحة.')
        serializer = TimetableEntrySerializer(
            entry,
            data={
                'timetable': entry.timetable_id,
                'day': day,
                'period': period.id,
                'classroom': entry.classroom_id,
                'subject': entry.subject_id,
                'teaching_assignment': entry.teaching_assignment_id,
            },
            partial=False,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TeacherAvailabilityViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = TeacherAvailabilitySerializer
    queryset = TeacherAvailability.objects.select_related('teacher')
    filterset_fields = ('teacher', 'day', 'is_available')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'timetable'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            self.required_permission = Permission.TIMETABLE_VIEW
        else:
            self.required_permission = Permission.TIMETABLE_MANAGE
        return super().get_permissions()
