from django.db.models import Exists, OuterRef, Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission, Role
from apps.subscriptions.permissions import RequiresFeature

from .models import Notification, NotificationAudience, NotificationPreference, NotificationRead, PreferenceCategory

MANAGER_ROLES = {Role.SUPER_ADMIN, Role.SCHOOL_OWNER, Role.SCHOOL_ADMIN, Role.ACCOUNTANT}


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    audience_label = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id',
            'type',
            'audience',
            'audience_label',
            'title',
            'body',
            'is_read',
            'user',
            'metadata',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_read', 'audience_label')

    def get_audience_label(self, obj):
        try:
            return NotificationAudience(obj.audience).label
        except ValueError:
            return obj.audience

    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            if hasattr(obj, 'is_read_by_me'):
                return bool(obj.is_read_by_me)
            return obj.reads.filter(user=request.user).exists()
        return bool(obj.is_read)

    def validate(self, attrs):
        audience = attrs.get('audience', getattr(self.instance, 'audience', NotificationAudience.ALL))
        user = attrs.get('user', getattr(self.instance, 'user', None))
        if audience == NotificationAudience.USER and user is None:
            raise serializers.ValidationError({'user': 'يجب تحديد المستخدم عند اختيار مستخدم محدد.'})
        if audience != NotificationAudience.USER:
            attrs['user'] = None
        return attrs


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ('id', 'category', 'enabled', 'updated_at')
        read_only_fields = ('id', 'updated_at')


class NotificationViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    filterset_fields = ('type', 'audience')
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'notifications'

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        request = self.request
        membership = getattr(request, 'membership', None)
        user = request.user

        qs = qs.annotate(
            is_read_by_me=Exists(
                NotificationRead.objects.filter(notification_id=OuterRef('pk'), user=user)
            )
        )

        if membership and membership.role in MANAGER_ROLES:
            # Managers see school-wide + manager-targeted + personal — not teacher/parent-only noise.
            return qs.filter(
                Q(user=user)
                | Q(
                    user__isnull=True,
                    audience__in=[
                        NotificationAudience.ALL,
                        NotificationAudience.MANAGERS,
                    ],
                )
            ).distinct()

        role = membership.role if membership else None
        personal = Q(user=user)
        if role == Role.TEACHER:
            targeted = Q(
                user__isnull=True,
                audience__in=[NotificationAudience.ALL, NotificationAudience.TEACHERS],
            )
        elif role == Role.PARENT:
            targeted = Q(
                user__isnull=True,
                audience__in=[NotificationAudience.ALL, NotificationAudience.PARENTS],
            )
        elif role == Role.STUDENT:
            targeted = Q(user__isnull=True, audience=NotificationAudience.ALL)
        else:
            targeted = Q(
                user__isnull=True,
                audience__in=[NotificationAudience.ALL, NotificationAudience.MANAGERS],
            )

        return qs.filter(personal | targeted).distinct()

    def get_permissions(self):
        if self.action in (
            'list',
            'retrieve',
            'mark_read',
            'mark_all_read',
            'unread_count',
            'preferences',
        ):
            self.required_permission = Permission.NOTIFICATIONS_VIEW
        else:
            self.required_permission = Permission.NOTIFICATIONS_MANAGE
        return super().get_permissions()

    def perform_create(self, serializer):
        audience = serializer.validated_data.get('audience', NotificationAudience.ALL)
        user = serializer.validated_data.get('user')
        if audience != NotificationAudience.USER:
            user = None
        serializer.save(school=self.get_school(), user=user, is_read=False)

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        is_read = self.request.query_params.get('is_read')
        if is_read is None:
            return qs
        value = str(is_read).lower() in ('1', 'true', 'yes')
        if value:
            return qs.filter(is_read_by_me=True)
        return qs.filter(is_read_by_me=False)

    @action(detail=True, methods=['post'], url_path='mark_read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        NotificationRead.objects.get_or_create(notification=notification, user=request.user)
        if notification.user_id == request.user.id:
            notification.is_read = True
            notification.save(update_fields=['is_read', 'updated_at'])
        # Ensure serializer annotation path sees the read without re-query.
        notification.is_read_by_me = True
        return Response(NotificationSerializer(notification, context={'request': request}).data)

    @action(detail=False, methods=['post'], url_path='mark_all_read')
    def mark_all_read(self, request):
        # Avoid .only() with Exists annotations — use values_list for reliability.
        qs = self.filter_queryset(self.get_queryset()).filter(is_read_by_me=False)
        ids = list(qs.values_list('id', flat=True))
        if ids:
            NotificationRead.objects.bulk_create(
                [NotificationRead(notification_id=nid, user=request.user) for nid in ids],
                ignore_conflicts=True,
            )
            Notification.objects.filter(id__in=ids, user_id=request.user.id).update(is_read=True)
        return Response({'status': 'ok', 'marked': len(ids)})

    @action(detail=False, methods=['get'], url_path='unread_count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read_by_me=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='preferences')
    def preferences(self, request):
        school = self.get_school()
        user = request.user
        if request.method == 'GET':
            prefs = NotificationPreference.objects.filter(school=school, user=user)
            existing = {p.category: p for p in prefs}
            rows = []
            for cat, label in PreferenceCategory.choices:
                pref = existing.get(cat)
                rows.append(
                    {
                        'category': cat,
                        'label': label,
                        'enabled': True if pref is None else pref.enabled,
                        'mandatory': cat == PreferenceCategory.ANNOUNCEMENTS,
                    }
                )
            return Response({'preferences': rows})

        items = request.data.get('preferences', request.data if isinstance(request.data, list) else [])
        if isinstance(request.data, dict) and 'category' in request.data:
            items = [request.data]
        updated = []
        for item in items:
            category = item.get('category')
            if category not in PreferenceCategory.values:
                continue
            if category == PreferenceCategory.ANNOUNCEMENTS:
                enabled = True
            else:
                enabled = bool(item.get('enabled', True))
            pref, _ = NotificationPreference.objects.update_or_create(
                school=school,
                user=user,
                category=category,
                defaults={'enabled': enabled},
            )
            updated.append(NotificationPreferenceSerializer(pref).data)
        return Response({'preferences': updated}, status=status.HTTP_200_OK)
