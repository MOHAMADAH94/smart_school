"""Event-driven notification helpers built on existing Notification model."""

from __future__ import annotations

from apps.notifications.models import (
    NotificationAudience,
    NotificationPreference,
    NotificationType,
    PreferenceCategory,
)
from apps.notifications.services import notify_audience, notify_user
from apps.parents.models import StudentParent
from apps.schools.models import SchoolMembership
from apps.schools.roles import Permission, Role, role_has_permission
from apps.subscriptions.models import NotificationEventLog


CATEGORY_BY_TYPE = {
    NotificationType.ATTENDANCE: PreferenceCategory.ATTENDANCE,
    NotificationType.GRADE: PreferenceCategory.GRADES,
    NotificationType.PAYMENT: PreferenceCategory.PAYMENTS,
    NotificationType.TRANSPORT: PreferenceCategory.TRANSPORTATION,
    NotificationType.ANNOUNCEMENT: PreferenceCategory.ANNOUNCEMENTS,
    NotificationType.ACADEMIC: PreferenceCategory.ACADEMIC,
    NotificationType.SUBSCRIPTION: PreferenceCategory.SUBSCRIPTION,
    NotificationType.SYSTEM: PreferenceCategory.SYSTEM,
}


def user_allows(school, user, notification_type: str, *, mandatory: bool = False) -> bool:
    if mandatory or notification_type == NotificationType.ANNOUNCEMENT:
        return True
    category = CATEGORY_BY_TYPE.get(notification_type)
    if not category:
        return True
    pref = NotificationPreference.objects.filter(
        school=school, user=user, category=category
    ).first()
    if pref is None:
        return True
    return pref.enabled


def notify_parent_users_for_student(
    *,
    school,
    student,
    title: str,
    body: str,
    type: str,
    metadata: dict | None = None,
    event_key: str | None = None,
) -> int:
    """Send USER notifications only to parents linked to this student."""
    if event_key:
        _, created = NotificationEventLog.objects.get_or_create(school=school, event_key=event_key)
        if not created:
            return 0

    links = (
        StudentParent.objects.filter(school=school, student=student)
        .select_related('parent', 'parent__user')
    )
    count = 0
    meta = {'student_id': student.id, **(metadata or {})}
    for link in links:
        parent = link.parent
        user = getattr(parent, 'user', None)
        if user is None:
            continue
        if not user_allows(school, user, type):
            continue
        notify_user(
            school=school,
            user=user,
            title=title,
            body=body,
            type=type,
            metadata=meta,
        )
        count += 1
    return count


def notify_finance_managers(*, school, title: str, body: str, metadata=None):
    memberships = SchoolMembership.objects.filter(
        school=school, is_active=True
    ).select_related('user')
    created = 0
    for m in memberships:
        if not role_has_permission(m.role, Permission.FINANCE_VIEW):
            continue
        if m.role == Role.TEACHER:
            continue
        if not user_allows(school, m.user, NotificationType.PAYMENT):
            continue
        notify_user(
            school=school,
            user=m.user,
            title=title,
            body=body,
            type=NotificationType.PAYMENT,
            metadata=metadata or {},
        )
        created += 1
    return created


def on_student_absent(*, school, student, date, event_dedupe: bool = True) -> int:
    name = student.full_name if hasattr(student, 'full_name') else str(student)
    key = f'student_absent:{school.id}:{student.id}:{date}' if event_dedupe else None
    return notify_parent_users_for_student(
        school=school,
        student=student,
        title=f'غياب {name}',
        body=f'{name} كان غائباً بتاريخ {date}.',
        type=NotificationType.ATTENDANCE,
        metadata={'date': str(date), 'event': 'StudentAbsent'},
        event_key=key,
    )


def on_grade_published(*, school, student, subject_name: str, assessment_name: str = '') -> int:
    name = student.full_name if hasattr(student, 'full_name') else str(student)
    return notify_parent_users_for_student(
        school=school,
        student=student,
        title=f'درجة جديدة لـ {name}',
        body=f'تم نشر درجة {subject_name} للطالب {name}'
        + (f' ({assessment_name}).' if assessment_name else '.'),
        type=NotificationType.GRADE,
        metadata={'event': 'GradePublished', 'subject': subject_name},
    )


def on_transport_assigned(*, school, student, bus_number: str) -> int:
    name = student.full_name if hasattr(student, 'full_name') else str(student)
    return notify_parent_users_for_student(
        school=school,
        student=student,
        title=f'تعيين نقل لـ {name}',
        body=f'تم تعيين {name} إلى الحافلة رقم {bus_number}.',
        type=NotificationType.TRANSPORT,
        metadata={'event': 'TransportAssigned', 'bus_number': bus_number},
    )


def on_subscription_payment_submitted(*, school, amount, currency='USD'):
    notify_audience(
        school=school,
        title='طلب دفع اشتراك جديد',
        body=f'تم تقديم طلب دفع بمبلغ {amount} {currency} بانتظار المراجعة.',
        type=NotificationType.SUBSCRIPTION,
        audience=NotificationAudience.MANAGERS,
        metadata={'event': 'PaymentSubmitted'},
    )


def on_subscription_payment_result(*, school, paid: bool, amount, currency='USD'):
    title = 'تم اعتماد دفع الاشتراك' if paid else 'تم رفض دفع الاشتراك'
    body = (
        f'تم اعتماد دفعة الاشتراك بمبلغ {amount} {currency}.'
        if paid
        else f'تم رفض دفعة الاشتراك بمبلغ {amount} {currency}.'
    )
    notify_audience(
        school=school,
        title=title,
        body=body,
        type=NotificationType.SUBSCRIPTION,
        audience=NotificationAudience.MANAGERS,
        metadata={'event': 'PaymentReceived' if paid else 'PaymentRejected'},
    )
