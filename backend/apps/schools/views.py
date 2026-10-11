from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import School, SchoolMembership
from .permissions import HasSchoolMembership, HasSchoolPermission, IsAuthenticatedAndActive
from .roles import Permission
from .serializers import CreateSchoolSerializer, SchoolMembershipSerializer, SchoolSerializer
from .services import get_user_memberships, membership_permissions


class CreateSchoolView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        serializer = CreateSchoolSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        school = serializer.save()
        membership = serializer.context['membership']
        return Response(
            {
                'message': 'تم إنشاء المدرسة بنجاح.',
                'school': SchoolSerializer(school, context={'request': request}).data,
                'membership': SchoolMembershipSerializer(membership).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MySchoolsView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = SchoolSerializer

    def get_queryset(self):
        memberships = get_user_memberships(self.request.user)
        return School.objects.filter(id__in=memberships.values_list('school_id', flat=True))


class SchoolDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]
    serializer_class = SchoolSerializer
    required_permission = Permission.SCHOOL_VIEW

    def get_permissions(self):
        perms = super().get_permissions()
        if self.request.method in ('PUT', 'PATCH'):
            self.required_permission = Permission.SCHOOL_MANAGE
        else:
            self.required_permission = Permission.SCHOOL_VIEW
        return perms

    def get_object(self):
        return self.request.school


class MembershipViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = SchoolMembershipSerializer

    def get_queryset(self):
        return get_user_memberships(self.request.user)


class CurrentContextView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def get(self, request):
        membership = getattr(request, 'membership', None)
        if membership is None:
            return Response(
                {
                    'has_school': False,
                    'membership': None,
                    'permissions': [],
                    'features': [],
                }
            )

        features = []
        try:
            from apps.subscriptions.services import get_enabled_features

            features = get_enabled_features(membership.school)
        except Exception:
            features = []

        return Response(
            {
                'has_school': True,
                'membership': SchoolMembershipSerializer(membership).data,
                'permissions': membership_permissions(membership),
                'features': features,
                'school': SchoolSerializer(membership.school, context={'request': request}).data,
            }
        )
