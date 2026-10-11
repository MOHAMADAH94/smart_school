from django.db.models import Avg
from rest_framework import serializers

from .models import AcademicTerm, Assessment, AssessmentType, Grade


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = (
            'id',
            'name',
            'academic_year',
            'start_date',
            'end_date',
            'is_current',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class AssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    assessment_type_label = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = (
            'id',
            'name',
            'assessment_type',
            'assessment_type_label',
            'subject',
            'subject_name',
            'classroom',
            'classroom_name',
            'term',
            'term_name',
            'max_score',
            'date',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'subject_name',
            'classroom_name',
            'term_name',
            'assessment_type_label',
        )

    def get_assessment_type_label(self, obj):
        try:
            return AssessmentType(obj.assessment_type).label
        except ValueError:
            return obj.assessment_type

    def validate(self, attrs):
        school = self.context['request'].school
        for field in ('subject', 'classroom', 'term'):
            obj = attrs.get(field) or getattr(self.instance, field, None)
            if obj and obj.school_id != school.id:
                raise serializers.ValidationError({field: 'لا ينتمي إلى هذه المدرسة.'})
        return attrs


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    assessment_name = serializers.CharField(source='assessment.name', read_only=True)
    max_score = serializers.DecimalField(
        source='assessment.max_score', max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Grade
        fields = (
            'id',
            'student',
            'student_name',
            'assessment',
            'assessment_name',
            'score',
            'max_score',
            'notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
            'student_name',
            'assessment_name',
            'max_score',
        )

    def validate(self, attrs):
        school = self.context['request'].school
        student = attrs.get('student') or getattr(self.instance, 'student', None)
        assessment = attrs.get('assessment') or getattr(self.instance, 'assessment', None)
        score = attrs.get('score', getattr(self.instance, 'score', None))
        if student and student.school_id != school.id:
            raise serializers.ValidationError({'student': 'الطالب لا ينتمي إلى هذه المدرسة.'})
        if assessment and assessment.school_id != school.id:
            raise serializers.ValidationError({'assessment': 'التقييم لا ينتمي إلى هذه المدرسة.'})
        if assessment and score is not None and score > assessment.max_score:
            raise serializers.ValidationError({'score': 'الدرجة أعلى من الحد الأقصى.'})
        return attrs


class GradeReportSerializer(serializers.Serializer):
    student_average = serializers.SerializerMethodField()
    subject_average = serializers.SerializerMethodField()
    classroom_average = serializers.SerializerMethodField()

    def _avg(self, qs):
        value = qs.aggregate(avg=Avg('score'))['avg']
        if value is None:
            return None
        return round(float(value), 2)

    def get_student_average(self, obj):
        student_id = self.context['request'].query_params.get('student')
        qs = obj
        if student_id:
            qs = qs.filter(student_id=student_id)
        return self._avg(qs)

    def get_subject_average(self, obj):
        subject_id = self.context['request'].query_params.get('subject')
        qs = obj
        if subject_id:
            qs = qs.filter(assessment__subject_id=subject_id)
        return self._avg(qs)

    def get_classroom_average(self, obj):
        classroom_id = self.context['request'].query_params.get('classroom')
        qs = obj
        if classroom_id:
            qs = qs.filter(assessment__classroom_id=classroom_id)
        return self._avg(qs)
