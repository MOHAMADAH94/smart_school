from rest_framework import serializers

from apps.students.models import Student

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_code = serializers.CharField(source='student.student_code', read_only=True)

    class Meta:
        model = Attendance
        fields = (
            'id',
            'student',
            'student_name',
            'student_code',
            'date',
            'status',
            'notes',
            'recorded_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'recorded_by',
            'created_at',
            'updated_at',
            'student_name',
            'student_code',
        )

    def validate_student(self, student):
        school = self.context['request'].school
        if student.school_id != school.id:
            raise serializers.ValidationError('الطالب لا ينتمي إلى هذه المدرسة.')
        return student


class BulkAttendanceSerializer(serializers.Serializer):
    classroom_id = serializers.IntegerField()
    date = serializers.DateField()
    default_status = serializers.ChoiceField(
        choices=['PRESENT', 'ABSENT', 'LATE', 'EXCUSED'],
        default='PRESENT',
    )
    records = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        school = self.context['request'].school
        classroom_id = attrs['classroom_id']
        from apps.academics.models import Classroom

        try:
            classroom = Classroom.objects.get(id=classroom_id, school=school)
        except Classroom.DoesNotExist as exc:
            raise serializers.ValidationError({'classroom_id': 'الفصل غير موجود.'}) from exc
        attrs['classroom'] = classroom
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        school = request.school
        classroom = validated_data['classroom']
        date = validated_data['date']
        default_status = validated_data['default_status']
        overrides = {
            int(item['student_id']): item
            for item in validated_data.get('records', [])
            if 'student_id' in item
        }

        students = Student.objects.filter(school=school, classroom=classroom, status='ACTIVE')
        results = []
        for student in students:
            payload = overrides.get(student.id, {})
            status_value = payload.get('status', default_status)
            notes = payload.get('notes', '')
            obj, _ = Attendance.objects.update_or_create(
                school=school,
                student=student,
                date=date,
                defaults={
                    'status': status_value,
                    'notes': notes,
                    'recorded_by': request.user,
                },
            )
            results.append(obj)
            if status_value == 'ABSENT':
                try:
                    from apps.notifications.events import on_student_absent

                    on_student_absent(school=school, student=student, date=date)
                except Exception:
                    pass
        return results
