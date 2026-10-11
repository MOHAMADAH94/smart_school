from django.db import models


class WeekDay(models.IntegerChoices):
    SUNDAY = 0, 'الأحد'
    MONDAY = 1, 'الإثنين'
    TUESDAY = 2, 'الثلاثاء'
    WEDNESDAY = 3, 'الأربعاء'
    THURSDAY = 4, 'الخميس'
    FRIDAY = 5, 'الجمعة'
    SATURDAY = 6, 'السبت'


class TimetableStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'مسودة'
    PUBLISHED = 'PUBLISHED', 'منشور'
    ARCHIVED = 'ARCHIVED', 'مؤرشف'


class Timetable(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='timetables',
    )
    name = models.CharField(max_length=128)
    academic_year = models.CharField(max_length=32)
    status = models.CharField(
        max_length=20,
        choices=TimetableStatus.choices,
        default=TimetableStatus.DRAFT,
    )
    # JSON list of WeekDay ints, e.g. [0,1,2,3,4]
    working_days = models.JSONField(default=list, blank=True)
    period_duration_minutes = models.PositiveIntegerField(default=45)
    notes = models.TextField(blank=True, default='')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('school', 'name', 'academic_year')

    def __str__(self) -> str:
        return f'{self.name} ({self.academic_year})'

    def get_working_days(self) -> list[int]:
        days = self.working_days or [0, 1, 2, 3, 4]
        return [int(d) for d in days]


class TimetablePeriod(models.Model):
    """Lesson/break slots shared across working days for a timetable."""

    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='periods',
    )
    period_number = models.PositiveIntegerField()
    label = models.CharField(max_length=64, blank=True, default='')
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)

    class Meta:
        ordering = ['period_number']
        unique_together = ('timetable', 'period_number')

    def __str__(self) -> str:
        name = self.label or f'الحصة {self.period_number}'
        return f'{name} ({self.start_time}-{self.end_time})'


class WeeklySubjectRequirement(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='weekly_subject_requirements',
    )
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='requirements',
    )
    classroom = models.ForeignKey(
        'academics.Classroom',
        on_delete=models.CASCADE,
        related_name='weekly_requirements',
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='weekly_requirements',
    )
    teaching_assignment = models.ForeignKey(
        'academics.TeachingAssignment',
        on_delete=models.PROTECT,
        related_name='weekly_requirements',
    )
    lessons_per_week = models.PositiveIntegerField()
    max_lessons_per_day = models.PositiveIntegerField(null=True, blank=True)
    preferred_lessons_per_day = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['classroom__name', 'subject__name']
        unique_together = ('timetable', 'classroom', 'subject')

    def __str__(self) -> str:
        return f'{self.classroom} / {self.subject} × {self.lessons_per_week}'


class TimetableEntry(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='timetable_entries',
    )
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    day = models.PositiveSmallIntegerField(choices=WeekDay.choices)
    period = models.ForeignKey(
        TimetablePeriod,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    classroom = models.ForeignKey(
        'academics.Classroom',
        on_delete=models.CASCADE,
        related_name='timetable_entries',
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='timetable_entries',
    )
    teaching_assignment = models.ForeignKey(
        'academics.TeachingAssignment',
        on_delete=models.PROTECT,
        related_name='timetable_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day', 'period__period_number']
        unique_together = ('timetable', 'day', 'period', 'classroom')
        constraints = [
            models.UniqueConstraint(
                fields=['timetable', 'day', 'period', 'teaching_assignment'],
                name='uniq_timetable_teacher_slot_via_assignment',
            ),
        ]

    def __str__(self) -> str:
        return f'D{self.day} P{self.period_id} {self.classroom} {self.subject}'


class TeacherAvailability(models.Model):
    """
    Optional availability rules.
    If no rows exist for a teacher, they are assumed fully available.
    is_available=False blocks the day (period null) or a specific period.
    """

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='teacher_availabilities',
    )
    teacher = models.ForeignKey(
        'teachers.Teacher',
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    day = models.PositiveSmallIntegerField(choices=WeekDay.choices)
    period_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Null = entire day rule',
    )
    is_available = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['teacher_id', 'day', 'period_number']
        unique_together = ('teacher', 'day', 'period_number')

    def __str__(self) -> str:
        return f'{self.teacher_id} D{self.day} P{self.period_number} avail={self.is_available}'
