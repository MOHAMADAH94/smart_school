from __future__ import annotations

from django.db import transaction

from apps.subscriptions.services import assign_trial_subscription

from .models import School, SchoolMembership
from .roles import Role, permissions_for_role, role_has_permission


def get_user_memberships(user):
    if not user or not user.is_authenticated:
        return SchoolMembership.objects.none()
    return (
        SchoolMembership.objects.filter(user=user, is_active=True, school__is_active=True)
        .select_related('school')
        .order_by('school__name')
    )


def get_membership_for_school(user, school_id: int | None):
    if not user or not user.is_authenticated or school_id is None:
        return None
    return (
        SchoolMembership.objects.filter(
            user=user,
            school_id=school_id,
            is_active=True,
            school__is_active=True,
        )
        .select_related('school')
        .first()
    )


def resolve_current_membership(user, requested_school_id=None):
    """
    Resolve active membership from an optional school id header/query.
    Never trusts a school_id without a valid membership.
    """
    memberships = list(get_user_memberships(user))
    if not memberships:
        return None

    if requested_school_id is not None:
        try:
            school_id = int(requested_school_id)
        except (TypeError, ValueError):
            return None
        for membership in memberships:
            if membership.school_id == school_id:
                return membership
        return None

    return memberships[0]


def user_has_permission(membership, permission: str) -> bool:
    if membership is None:
        return False
    return role_has_permission(membership.role, permission)


def membership_permissions(membership) -> list[str]:
    if membership is None:
        return []
    perms = permissions_for_role(membership.role)
    if '*' in perms:
        return sorted(
            {
                p
                for role_perms in __import__(
                    'apps.schools.roles', fromlist=['ROLE_PERMISSIONS']
                ).ROLE_PERMISSIONS.values()
                for p in role_perms
                if p != '*'
            }
        )
    return sorted(perms)


@transaction.atomic
def create_school_with_owner(*, user, school_data: dict) -> tuple[School, SchoolMembership]:
    school = School.objects.create(**school_data)
    membership = SchoolMembership.objects.create(
        user=user,
        school=school,
        role=Role.SCHOOL_OWNER,
        is_active=True,
    )
    assign_trial_subscription(school)
    return school, membership
