import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from .roles import Role


def generate_school_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class School(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='schools/logos/', blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.CharField(max_length=512, blank=True, default='')
    city = models.CharField(max_length=128, blank=True, default='')
    country = models.CharField(max_length=128, blank=True, default='')
    academic_year = models.CharField(max_length=32, blank=True, default='')
    school_code = models.CharField(max_length=32, unique=True, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.school_code:
            code = generate_school_code()
            while School.objects.filter(school_code=code).exists():
                code = generate_school_code()
            self.school_code = code
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'school'
            slug = base
            counter = 1
            while School.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class SchoolMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    role = models.CharField(max_length=32, choices=Role.CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'school')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.user} @ {self.school} ({self.role})'
