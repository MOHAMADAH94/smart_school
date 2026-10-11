from rest_framework import serializers

from apps.teachers.models import Teacher

from .models import Classroom, GradeLevel, Subject, TeachingAssignment


class GradeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ('id', 'name', 'order', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ClassroomSerializer(serializers.ModelSerializer):
    grade_level_name = serializers.CharField(source='grade_level.name', read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Classroom
        fields = (
            'id',
            'name',
            'section',
            'capacity',
            'grade_level',
            'grade_level_name',
            'student_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'grade_level_name',
            'student_count',
        )

    def validate_grade_level(self, grade_level):
        school = self.context['request'].school
        if grade_level.school_id != school.id:
            raise serializers.ValidationError('المرحلة لا تنتمي إلى هذه المدرسة.')
        return grade_level

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('student_count') is None:
            data['student_count'] = instance.students.count()
        return data


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ('id', 'name', 'code', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)

    class Meta:
        model = TeachingAssignment
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'subject',
            'subject_name',
            'classroom',
            'classroom_name',
            'created_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'teacher_name',
            'subject_name',
            'classroom_name',
        )

    def validate(self, attrs):
        school = self.context['request'].school
        teacher = attrs.get('teacher') or getattr(self.instance, 'teacher', None)
        subject = attrs.get('subject') or getattr(self.instance, 'subject', None)
        classroom = attrs.get('classroom') or getattr(self.instance, 'classroom', None)
        for obj, label in (
            (teacher, 'teacher'),
            (subject, 'subject'),
            (classroom, 'classroom'),
        ):
            if obj and obj.school_id != school.id:
                raise serializers.ValidationError({label: 'العنصر لا ينتمي إلى هذه المدرسة.'})
        return attrs
