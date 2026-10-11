from rest_framework import serializers

from apps.academics.models import Classroom

from .models import Student


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True, default=None)

    class Meta:
        model = Student
        fields = (
            'id',
            'student_code',
            'first_name',
            'father_name',
            'last_name',
            'full_name',
            'gender',
            'date_of_birth',
            'phone',
            'address',
            'enrollment_date',
            'status',
            'classroom',
            'classroom_name',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'full_name', 'classroom_name')

    def validate_classroom(self, classroom):
        if classroom is None:
            return classroom
        school = self.context['request'].school
        if classroom.school_id != school.id:
            raise serializers.ValidationError('الفصل لا ينتمي إلى هذه المدرسة.')
        return classroom
