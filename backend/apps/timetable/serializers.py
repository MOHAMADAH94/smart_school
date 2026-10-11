from rest_framework import serializers

from apps.academics.models import TeachingAssignment

from .models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    WeeklySubjectRequirement,
)
from .services import validate_entry_payload


class TimetablePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetablePeriod
        fields = (
            'id',
            'timetable',
            'period_number',
            'label',
            'start_time',
            'end_time',
            'is_break',
        )
        read_only_fields = ('id',)


class TimetableSerializer(serializers.ModelSerializer):
    periods = TimetablePeriodSerializer(many=True, required=False)
    entries_count = serializers.IntegerField(source='entries.count', read_only=True)
    requirements_count = serializers.IntegerField(source='requirements.count', read_only=True)

    class Meta:
        model = Timetable
        fields = (
            'id',
            'name',
            'academic_year',
            'status',
            'working_days',
            'period_duration_minutes',
            'notes',
            'published_at',
            'periods',
            'entries_count',
            'requirements_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'status', 'published_at', 'created_at', 'updated_at', 'entries_count', 'requirements_count')

    def create(self, validated_data):
        periods_data = validated_data.pop('periods', None)
        validated_data.pop('school', None)
        school = self.context['request'].school
        if not validated_data.get('working_days'):
            validated_data['working_days'] = [0, 1, 2, 3, 4]
        timetable = Timetable.objects.create(school=school, **validated_data)
        if periods_data:
            for p in periods_data:
                TimetablePeriod.objects.create(timetable=timetable, **p)
        elif not timetable.periods.exists():
            # Default 7 periods of 45 minutes starting 08:00 with a mid break
            from datetime import datetime, timedelta

            start = datetime.strptime('08:00', '%H:%M')
            duration = timedelta(minutes=timetable.period_duration_minutes or 45)
            break_after = 3
            num = 1
            for i in range(1, 8):
                if i == break_after + 1:
                    end = start + timedelta(minutes=15)
                    TimetablePeriod.objects.create(
                        timetable=timetable,
                        period_number=num,
                        label='استراحة',
                        start_time=start.time(),
                        end_time=end.time(),
                        is_break=True,
                    )
                    start = end
                    num += 1
                end = start + duration
                TimetablePeriod.objects.create(
                    timetable=timetable,
                    period_number=num,
                    label=f'الحصة {i}',
                    start_time=start.time(),
                    end_time=end.time(),
                    is_break=False,
                )
                start = end
                num += 1
        return timetable

    def update(self, instance, validated_data):
        validated_data.pop('periods', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Prefer annotated counts when present
        if hasattr(instance, 'entries_count_ann'):
            data['entries_count'] = instance.entries_count_ann
        if hasattr(instance, 'requirements_count_ann'):
            data['requirements_count'] = instance.requirements_count_ann
        return data


class WeeklySubjectRequirementSerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    scheduled_count = serializers.SerializerMethodField()

    class Meta:
        model = WeeklySubjectRequirement
        fields = (
            'id',
            'timetable',
            'classroom',
            'classroom_name',
            'subject',
            'subject_name',
            'teaching_assignment',
            'teacher_name',
            'lessons_per_week',
            'max_lessons_per_day',
            'preferred_lessons_per_day',
            'notes',
            'scheduled_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'classroom_name', 'subject_name', 'teacher_name', 'scheduled_count')

    def get_teacher_name(self, obj):
        return str(obj.teaching_assignment.teacher)

    def get_scheduled_count(self, obj):
        return obj.timetable.entries.filter(classroom_id=obj.classroom_id, subject_id=obj.subject_id).count()

    def validate(self, attrs):
        request = self.context['request']
        school = request.school
        timetable = attrs.get('timetable') or getattr(self.instance, 'timetable', None)
        classroom = attrs.get('classroom') or getattr(self.instance, 'classroom', None)
        subject = attrs.get('subject') or getattr(self.instance, 'subject', None)
        ta = attrs.get('teaching_assignment') or getattr(self.instance, 'teaching_assignment', None)
        if timetable and timetable.school_id != school.id:
            raise serializers.ValidationError({'timetable': 'جدول غير صالح.'})
        if classroom and classroom.school_id != school.id:
            raise serializers.ValidationError({'classroom': 'فصل غير صالح.'})
        if subject and subject.school_id != school.id:
            raise serializers.ValidationError({'subject': 'مادة غير صالحة.'})
        if ta:
            if ta.school_id != school.id:
                raise serializers.ValidationError({'teaching_assignment': 'تكليف غير صالح.'})
            if classroom and ta.classroom_id != classroom.id:
                raise serializers.ValidationError({'teaching_assignment': 'التكليف لا يطابق الفصل.'})
            if subject and ta.subject_id != subject.id:
                raise serializers.ValidationError({'teaching_assignment': 'التكليف لا يطابق المادة.'})
        lessons = attrs.get('lessons_per_week', getattr(self.instance, 'lessons_per_week', None))
        if lessons is not None and lessons < 1:
            raise serializers.ValidationError({'lessons_per_week': 'يجب أن يكون العدد 1 على الأقل.'})
        return attrs

    def create(self, validated_data):
        validated_data['school'] = self.context['request'].school
        return super().create(validated_data)


class TimetableEntrySerializer(serializers.ModelSerializer):
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    period_number = serializers.IntegerField(source='period.period_number', read_only=True)
    period_label = serializers.CharField(source='period.label', read_only=True)
    start_time = serializers.TimeField(source='period.start_time', read_only=True)
    end_time = serializers.TimeField(source='period.end_time', read_only=True)

    class Meta:
        model = TimetableEntry
        fields = (
            'id',
            'timetable',
            'day',
            'period',
            'period_number',
            'period_label',
            'start_time',
            'end_time',
            'classroom',
            'classroom_name',
            'subject',
            'subject_name',
            'teaching_assignment',
            'teacher_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'classroom_name',
            'subject_name',
            'teacher_name',
            'period_number',
            'period_label',
            'start_time',
            'end_time',
        )

    def get_teacher_name(self, obj):
        return str(obj.teaching_assignment.teacher)

    def validate(self, attrs):
        request = self.context['request']
        school = request.school
        instance = self.instance
        timetable = attrs.get('timetable') or getattr(instance, 'timetable', None)
        day = attrs.get('day', getattr(instance, 'day', None))
        period = attrs.get('period') or getattr(instance, 'period', None)
        classroom = attrs.get('classroom') or getattr(instance, 'classroom', None)
        subject = attrs.get('subject') or getattr(instance, 'subject', None)
        ta = attrs.get('teaching_assignment') or getattr(instance, 'teaching_assignment', None)

        if not all([timetable, period, classroom, subject, ta]) or day is None:
            raise serializers.ValidationError('بيانات الحصة غير مكتملة.')

        issues = validate_entry_payload(
            school=school,
            timetable=timetable,
            day=day,
            period=period,
            classroom_id=classroom.id,
            subject_id=subject.id,
            teaching_assignment=ta,
            exclude_entry_id=instance.id if instance else None,
        )
        errors = [i for i in issues if i.severity == 'error']
        if errors:
            raise serializers.ValidationError(
                {'conflicts': [e.message_ar for e in errors], 'detail': errors[0].message_ar}
            )
        return attrs

    def create(self, validated_data):
        validated_data['school'] = self.context['request'].school
        return super().create(validated_data)


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = TeacherAvailability
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'day',
            'period_number',
            'is_available',
            'notes',
        )
        read_only_fields = ('id', 'teacher_name')

    def get_teacher_name(self, obj):
        return str(obj.teacher)

    def create(self, validated_data):
        validated_data['school'] = self.context['request'].school
        return super().create(validated_data)
