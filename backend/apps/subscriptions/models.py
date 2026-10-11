from django.conf import settings
from django.db import models
from django.utils import timezone


class Feature(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self) -> str:
        return self.code


class SubscriptionPlan(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    price_annual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default='USD')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    features = models.ManyToManyField(Feature, through='PlanFeature', related_name='plans')

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self) -> str:
        return self.name


class PlanFeature(models.Model):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='plan_features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='plan_features')
    is_enabled = models.BooleanField(default=True)
    limit_value = models.IntegerField(null=True, blank=True, help_text='Optional numeric limit')

    class Meta:
        unique_together = ('plan', 'feature')

    def __str__(self) -> str:
        return f'{self.plan.code}:{self.feature.code}'


class SubscriptionStatus(models.TextChoices):
    TRIAL = 'TRIAL', 'Trial'
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Subscription(models.Model):
    school = models.OneToOneField(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.school} — {self.plan} ({self.status})'

    @property
    def is_access_allowed(self) -> bool:
        return True

    @property
    def days_remaining(self) -> int:
        today = timezone.localdate()
        return (self.end_date - today).days

    @property
    def display_status(self) -> str:
        """Dynamic UI status; EXPIRING_SOON is not stored."""
        self.refresh_status()
        if self.status == SubscriptionStatus.CANCELLED:
            return 'CANCELLED'
        if self.status == SubscriptionStatus.EXPIRED or self.days_remaining < 0:
            return 'EXPIRED'
        if self.status == SubscriptionStatus.TRIAL:
            if self.days_remaining <= 7:
                return 'EXPIRING_SOON'
            return 'TRIAL'
        if self.days_remaining <= 30:
            return 'EXPIRING_SOON'
        return 'ACTIVE'

    def refresh_status(self) -> None:
        today = timezone.localdate()
        if self.status == SubscriptionStatus.CANCELLED:
            return
        if self.end_date < today and self.status != SubscriptionStatus.EXPIRED:
            self.status = SubscriptionStatus.EXPIRED
            self.save(update_fields=['status', 'updated_at'])


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Cash'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
    MANUAL_PAYMENT = 'MANUAL_PAYMENT', 'Manual Payment'
    ONLINE = 'ONLINE', 'Online'
    OTHER = 'OTHER', 'Other'


class SubscriptionPaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PAID = 'PAID', 'Paid'
    FAILED = 'FAILED', 'Failed'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    REFUNDED = 'REFUNDED', 'Refunded'


class SubscriptionPayment(models.Model):
    """SaaS subscription payment (separate from student fee payments in finance)."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='subscription_payments',
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default='USD')
    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
    )
    transaction_reference = models.CharField(max_length=128, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=SubscriptionPaymentStatus.choices,
        default=SubscriptionPaymentStatus.PENDING,
    )
    paid_at = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    receipt_file = models.FileField(upload_to='subscription_receipts/', null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_subscription_payments',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_subscription_payments',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.school_id} {self.amount} {self.status}'


class NotificationEventLog(models.Model):
    """Dedup log for automatic subscription/system notification events."""

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='notification_event_logs',
    )
    event_key = models.CharField(max_length=191)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('school', 'event_key')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.event_key
