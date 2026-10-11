from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    SYSTEM = 'SYSTEM', 'نظام'
    ATTENDANCE = 'ATTENDANCE', 'حضور'
    GRADE = 'GRADE', 'درجات'
    PAYMENT = 'PAYMENT', 'مدفوعات'
    ANNOUNCEMENT = 'ANNOUNCEMENT', 'إعلان'
    TRANSPORT = 'TRANSPORT', 'نقل'
    SUBSCRIPTION = 'SUBSCRIPTION', 'اشتراك'
    ACADEMIC = 'ACADEMIC', 'أكاديمي'


class PreferenceCategory(models.TextChoices):
    ATTENDANCE = 'ATTENDANCE', 'حضور'
    GRADES = 'GRADES', 'درجات'
    PAYMENTS = 'PAYMENTS', 'مدفوعات'
    TRANSPORTATION = 'TRANSPORTATION', 'نقل'
    ANNOUNCEMENTS = 'ANNOUNCEMENTS', 'إعلانات'
    ACADEMIC = 'ACADEMIC', 'أكاديمي'
    SCHEDULE = 'SCHEDULE', 'جدول'
    SUBSCRIPTION = 'SUBSCRIPTION', 'اشتراك'
    SYSTEM = 'SYSTEM', 'نظام'


class NotificationAudience(models.TextChoices):
    ALL = 'ALL', 'الجميع'
    TEACHERS = 'TEACHERS', 'المعلمون فقط'
    PARENTS = 'PARENTS', 'أولياء الأمور فقط'
    MANAGERS = 'MANAGERS', 'الإدارة فقط'
    USER = 'USER', 'مستخدم محدد'


class Notification(models.Model):
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text='عند التحديد يكون الإشعار لمستخدم واحد (audience=USER).',
    )
    audience = models.CharField(
        max_length=20,
        choices=NotificationAudience.choices,
        default=NotificationAudience.ALL,
    )
    type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    is_read = models.BooleanField(
        default=False,
        help_text='للتوافق؛ حالة القراءة الفعلية للجمهور تُدار عبر NotificationRead.',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title


class NotificationRead(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='reads',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_reads',
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('notification', 'user')
        ordering = ['-read_at']

    def __str__(self) -> str:
        return f'{self.user_id} read {self.notification_id}'


class NotificationPreference(models.Model):
    """Per-user category preferences. School announcements cannot be disabled."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
    )
    category = models.CharField(max_length=32, choices=PreferenceCategory.choices)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school', 'user', 'category')
        ordering = ['category']

    def __str__(self) -> str:
        return f'{self.user_id}:{self.category}={"on" if self.enabled else "off"}'
