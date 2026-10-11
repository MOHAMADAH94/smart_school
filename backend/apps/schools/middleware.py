from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .services import resolve_current_membership


class CurrentSchoolMiddleware:
    """
    Attach request.membership / request.school / request.school_id
    based on authenticated membership — never trust school_id alone.

    JWT is validated here because DRF authentication runs too late for
    middleware-based tenant resolution.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        request.membership = None
        request.school = None
        request.school_id = None

        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            try:
                result = self.jwt_auth.authenticate(request)
                if result is not None:
                    request.user, request.auth = result
                    user = request.user
            except (InvalidToken, TokenError, Exception):
                user = getattr(request, 'user', None)

        if user and getattr(user, 'is_authenticated', False):
            requested = request.META.get(settings.SCHOOL_HEADER) or request.GET.get(
                'school_id'
            )
            membership = resolve_current_membership(user, requested)
            if membership:
                request.membership = membership
                request.school = membership.school
                request.school_id = membership.school_id

        return self.get_response(request)
