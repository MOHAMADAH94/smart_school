from rest_framework.permissions import BasePermission

from .services import user_has_permission


class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class HasSchoolMembership(BasePermission):
    """Requires a valid resolved school membership on the request."""

    message = 'لا توجد عضوية مدرسة نشطة.'

    def has_permission(self, request, view):
        return bool(getattr(request, 'membership', None))


class HasSchoolPermission(BasePermission):
    """
    Check fine-grained permission against the current membership role.
    Set `required_permission` on the view.
    """

    message = 'ليس لديك صلاحية لتنفيذ هذا الإجراء.'

    def has_permission(self, request, view):
        membership = getattr(request, 'membership', None)
        permission = getattr(view, 'required_permission', None)
        if permission is None:
            return membership is not None
        return user_has_permission(membership, permission)


class IsSchoolOwnerOrAdmin(BasePermission):
    message = 'يتطلب صلاحية مالك أو مدير المدرسة.'

    def has_permission(self, request, view):
        membership = getattr(request, 'membership', None)
        if membership is None:
            return False
        return membership.role in {'SUPER_ADMIN', 'SCHOOL_OWNER', 'SCHOOL_ADMIN'}
