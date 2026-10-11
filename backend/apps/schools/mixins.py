"""Shared mixins for tenant-scoped ViewSets."""

from rest_framework.exceptions import PermissionDenied

from apps.schools.permissions import HasSchoolMembership, HasSchoolPermission, IsAuthenticatedAndActive


class TenantQuerysetMixin:
    """
    Filter queryset by request.school and reject cross-tenant writes.
    Views using this mixin must set `school_field` if not 'school'.
    """

    school_field = 'school'
    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]

    def get_school(self):
        school = getattr(self.request, 'school', None)
        if school is None:
            raise PermissionDenied('لا توجد مدرسة نشطة.')
        return school

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.school_field: self.get_school()})

    def perform_create(self, serializer):
        serializer.save(**{self.school_field: self.get_school()})
