from django.db import models


class AcademicTerm(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='terms',
    )
    name = models.CharField(max_length=128)
    academic_year = models.CharField(max_length=32)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-academic_year', 'name']
        unique_together = ('school', 'name', 'academic_year')

    def __str__(self) -> str:
        return f'{self.name} ({self.academic_year})'


class AssessmentType(models.TextChoices):
    QUIZ = 'QUIZ', 'مذاكرة'
    HOMEWORK = 'HOMEWORK', 'واجب'
    MIDTERM = 'MIDTERM', 'امتحان نصفي'
    FINAL = 'FINAL', 'امتحان نهائي فصلي'
    OTHER = 'OTHER', 'أخرى'


class Assessment(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='assessments',
    )
    name = models.CharField(max_length=128)
    assessment_type = models.CharField(
        max_length=16,
        choices=AssessmentType.choices,
        default=AssessmentType.QUIZ,
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='assessments',
    )
    classroom = models.ForeignKey(
        'academics.Classroom',
        on_delete=models.CASCADE,
        related_name='assessments',
    )
    term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.CASCADE,
        related_name='assessments',
    )
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=100)
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'name']

    def __str__(self) -> str:
        return self.name


class Grade(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='grades',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='grades',
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='grades',
    )
    score = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'assessment')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.student} — {self.assessment}: {self.score}'
