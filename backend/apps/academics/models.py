from django.db import models


class GradeLevel(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='grade_levels',
    )
    name = models.CharField(max_length=128)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ('school', 'name')

    def __str__(self) -> str:
        return self.name


class Classroom(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='classrooms',
    )
    grade_level = models.ForeignKey(
        GradeLevel,
        on_delete=models.PROTECT,
        related_name='classrooms',
    )
    name = models.CharField(max_length=128)
    section = models.CharField(max_length=32, blank=True, default='')
    capacity = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['grade_level__order', 'name']
        unique_together = ('school', 'name')

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('school', 'code')

    def __str__(self) -> str:
        return f'{self.code} — {self.name}'


class TeachingAssignment(models.Model):
    """Teacher ↔ Subject ↔ Classroom assignment within a school."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher', 'subject', 'classroom')

    def __str__(self) -> str:
        return f'{self.teacher} / {self.subject} / {self.classroom}'
