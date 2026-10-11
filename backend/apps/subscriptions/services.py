from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Feature,
    NotificationEventLog,
    PlanFeature,
    Subscription,
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
)

BASIC_FEATURES = [
    ('students', 'Students'),
    ('teachers', 'Teachers'),
    ('classes', 'Classes'),
    ('subjects', 'Subjects'),
    ('attendance', 'Attendance'),
    ('grades', 'Grades'),
    ('parents', 'Parents'),
    ('transport', 'Transport'),
    ('basic_reports', 'Basic Reports'),
]

PROFESSIONAL_EXTRA = [
    ('accounting', 'Accounting'),
    ('fees', 'Fees'),
    ('payments', 'Payments'),
    ('expenses', 'Expenses'),
    ('advanced_reports', 'Advanced Reports'),
    ('notifications', 'Notifications'),
    ('parent_portal', 'Parent Portal'),
    ('student_portal', 'Student Portal'),
    ('timetable', 'Timetable'),
]

EXPIRY_WARNING_DAYS = (30, 14, 7, 3, 1)


@transaction.atomic
def ensure_default_plans() -> None:
    for code, name in BASIC_FEATURES + PROFESSIONAL_EXTRA:
        Feature.objects.get_or_create(code=code, defaults={'name': name})

    basic, _ = SubscriptionPlan.objects.get_or_create(
        code='basic',
        defaults={
            'name': 'Basic',
            'description': 'Core school management features',
            'price_annual': Decimal('499.00'),
            'currency': 'USD',
            'sort_order': 1,
        },
    )
    if basic.price_annual == 0:
        basic.price_annual = Decimal('499.00')
        basic.save(update_fields=['price_annual'])

    pro, _ = SubscriptionPlan.objects.get_or_create(
        code='professional',
        defaults={
            'name': 'Professional',
            'description': 'Basic plus accounting, portals, and notifications',
            'price_annual': Decimal('999.00'),
            'currency': 'USD',
            'sort_order': 2,
        },
    )
    if pro.price_annual == 0:
        pro.price_annual = Decimal('999.00')
        pro.save(update_fields=['price_annual'])

    for code, _name in BASIC_FEATURES:
        feature = Feature.objects.get(code=code)
        PlanFeature.objects.get_or_create(plan=basic, feature=feature, defaults={'is_enabled': True})
        PlanFeature.objects.get_or_create(plan=pro, feature=feature, defaults={'is_enabled': True})

    for code, _name in PROFESSIONAL_EXTRA:
        feature = Feature.objects.get(code=code)
        PlanFeature.objects.get_or_create(plan=basic, feature=feature, defaults={'is_enabled': False})
        PlanFeature.objects.get_or_create(plan=pro, feature=feature, defaults={'is_enabled': True})


def assign_trial_subscription(school, plan_code: str = 'professional', days: int = 30) -> Subscription:
    ensure_default_plans()
    plan = SubscriptionPlan.objects.get(code=plan_code)
    start = timezone.localdate()
    end = start + timedelta(days=days)
    subscription, created = Subscription.objects.get_or_create(
        school=school,
        defaults={
            'plan': plan,
            'start_date': start,
            'end_date': end,
            'status': SubscriptionStatus.TRIAL,
        },
    )
    if not created:
        subscription.plan = plan
        subscription.start_date = start
        subscription.end_date = end
        subscription.status = SubscriptionStatus.TRIAL
        subscription.save()
    return subscription


def get_school_subscription(school) -> Subscription | None:
    try:
        subscription = school.subscription
    except Subscription.DoesNotExist:
        return None
    subscription.refresh_status()
    return subscription


def get_enabled_features(school) -> list[str]:
    subscription = get_school_subscription(school)
    if subscription is None:
        return []
    qs = subscription.plan.plan_features.filter(is_enabled=True).select_related('feature')
    enabled = [pf.feature.code for pf in qs if pf.feature.is_active]
    if subscription.status in {SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED}:
        basic_codes = {c for c, _ in BASIC_FEATURES}
        return [c for c in enabled if c in basic_codes]
    return enabled


def school_has_feature(school, feature_code: str) -> bool:
    return feature_code in get_enabled_features(school)


def compute_renewal_period(subscription: Subscription, paid_on=None) -> tuple:
    """
    Annual renewal rules:
    - If still active/trial and end_date >= paid_on: extend from current end_date (+1 year)
    - If expired: start from payment date, end = start + 1 year
    """
    paid_on = paid_on or timezone.localdate()
    today = timezone.localdate()
    still_valid = (
        subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL}
        and subscription.end_date >= paid_on
        and subscription.end_date >= today
    )
    if still_valid:
        period_start = subscription.end_date
        period_end = subscription.end_date + timedelta(days=365)
    else:
        period_start = paid_on
        period_end = paid_on + timedelta(days=365)
    return period_start, period_end


@transaction.atomic
def apply_paid_subscription_payment(payment: SubscriptionPayment, reviewer=None) -> Subscription:
    """Mark payment PAID and activate/extend the school's subscription."""
    if payment.status == SubscriptionPaymentStatus.PAID:
        return payment.subscription

    subscription = payment.subscription
    paid_on = payment.paid_at or timezone.localdate()
    period_start, period_end = compute_renewal_period(subscription, paid_on=paid_on)

    payment.status = SubscriptionPaymentStatus.PAID
    payment.period_start = period_start
    payment.period_end = period_end
    payment.paid_at = paid_on
    payment.reviewed_by = reviewer
    payment.reviewed_at = timezone.now()
    payment.save()

    today = timezone.localdate()
    still_valid = (
        subscription.status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL}
        and subscription.end_date >= paid_on
        and subscription.end_date >= today
    )

    subscription.plan = payment.plan
    if still_valid:
        # Keep original start; extend from current end_date (period_end from compute_renewal_period).
        subscription.end_date = period_end
    else:
        subscription.start_date = period_start
        subscription.end_date = period_end
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.save()

    return subscription


@transaction.atomic
def reject_subscription_payment(payment: SubscriptionPayment, reviewer=None, notes: str = '') -> SubscriptionPayment:
    payment.status = SubscriptionPaymentStatus.REJECTED
    payment.reviewed_by = reviewer
    payment.reviewed_at = timezone.now()
    payment.review_notes = notes
    payment.save(
        update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes', 'updated_at']
    )
    return payment


def latest_payment_status(subscription: Subscription | None) -> str | None:
    if subscription is None:
        return None
    payment = subscription.payments.order_by('-created_at').first()
    return payment.status if payment else None


def emit_subscription_expiry_warnings(school) -> list[str]:
    """
    Create at-most-once expiry notifications using NotificationEventLog keys.
    Returns list of event keys emitted in this call.
    """
    from apps.notifications.models import NotificationAudience, NotificationType
    from apps.notifications.services import notify_audience

    subscription = get_school_subscription(school)
    if subscription is None:
        return []

    emitted: list[str] = []
    days = subscription.days_remaining

    def _emit(event_key: str, title: str, body: str) -> None:
        _, created = NotificationEventLog.objects.get_or_create(
            school=school,
            event_key=event_key,
        )
        if not created:
            return
        notify_audience(
            school=school,
            title=title,
            body=body,
            type=NotificationType.SUBSCRIPTION,
            audience=NotificationAudience.MANAGERS,
            metadata={'source': 'subscription_expiry', 'event_key': event_key},
        )
        emitted.append(event_key)

    if days < 0 or subscription.status == SubscriptionStatus.EXPIRED:
        _emit(
            f'subscription_expiry:{school.id}:expired',
            'انتهى اشتراك المدرسة',
            'انتهت صلاحية الاشتراك. تم تقييد الميزات الاحترافية. يرجى تجديد الاشتراك.',
        )
        return emitted

    for threshold in EXPIRY_WARNING_DAYS:
        if days == threshold:
            _emit(
                f'subscription_expiry:{school.id}:{threshold}',
                f'تبقّى {threshold} يوماً على انتهاء الاشتراك',
                f'ينتهي اشتراك خطتك {subscription.plan.name} خلال {threshold} يوماً ({subscription.end_date}).',
            )
    return emitted
