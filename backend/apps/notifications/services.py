"""Helpers to create in-app notifications for school users."""

from __future__ import annotations

from apps.notifications.models import Notification, NotificationAudience, NotificationType


def notify_user(
    *,
    school,
    title: str,
    body: str = '',
    type: str = NotificationType.SYSTEM,
    user=None,
    audience: str | None = None,
    metadata: dict | None = None,
) -> Notification:
    if user is not None:
        audience = NotificationAudience.USER
    elif not audience:
        audience = NotificationAudience.ALL
    return Notification.objects.create(
        school=school,
        user=user,
        audience=audience,
        type=type,
        title=title,
        body=body,
        metadata=metadata or {},
    )


def notify_audience(
    *,
    school,
    title: str,
    body: str = '',
    type: str = NotificationType.ANNOUNCEMENT,
    audience: str = NotificationAudience.ALL,
    metadata: dict | None = None,
) -> Notification:
    return notify_user(
        school=school,
        title=title,
        body=body,
        type=type,
        user=None,
        audience=audience,
        metadata=metadata,
    )


def notify_school(
    *,
    school,
    title: str,
    body: str = '',
    type: str = NotificationType.ANNOUNCEMENT,
    metadata: dict | None = None,
) -> Notification:
    """Broadcast notification visible to all members."""
    return notify_audience(
        school=school,
        title=title,
        body=body,
        type=type,
        audience=NotificationAudience.ALL,
        metadata=metadata,
    )


def notify_teachers(*, school, title: str, body: str = '', type: str = NotificationType.ACADEMIC, metadata=None):
    return notify_audience(
        school=school,
        title=title,
        body=body,
        type=type,
        audience=NotificationAudience.TEACHERS,
        metadata=metadata,
    )


def notify_parents(*, school, title: str, body: str = '', type: str = NotificationType.ANNOUNCEMENT, metadata=None):
    return notify_audience(
        school=school,
        title=title,
        body=body,
        type=type,
        audience=NotificationAudience.PARENTS,
        metadata=metadata,
    )
