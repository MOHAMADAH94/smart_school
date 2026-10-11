from rest_framework.permissions import BasePermission

from apps.subscriptions.services import school_has_feature


class RequiresFeature(BasePermission):
    """
    Gate endpoints by subscription feature code.
    Set `required_feature` on the view.
    """

    message = 'هذه الميزة غير متاحة في خطتك الحالية.'

    def has_permission(self, request, view):
        feature = getattr(view, 'required_feature', None)
        if not feature:
            return True
        school = getattr(request, 'school', None)
        if school is None:
            return False
        return school_has_feature(school, feature)
