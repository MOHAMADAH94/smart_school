from django.conf import settings
from django.db import models


class StudentStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    GRADUATED = 'GRADUATED', 'Graduated'
    TRANSFERRED = 'TRANSFERRED', 'Transferred'


class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'


class Student(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='students',
    )
    student_code = models.CharField(max_length=64)
    first_name = models.CharField(max_length=128)
    father_name = models.CharField(max_length=128, blank=True, default='')
    last_name = models.CharField(max_length=128)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True, default='')
    address = models.CharField(max_length=512, blank=True, default='')
    enrollment_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE,
    )
    classroom = models.ForeignKey(
        'academics.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
    )
    notes = models.TextField(blank=True, default='')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profiles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name']
        unique_together = ('school', 'student_code')

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.father_name, self.last_name]
        return ' '.join(p for p in parts if p)
