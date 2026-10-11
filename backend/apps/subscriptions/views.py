from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.permissions import HasSchoolMembership, HasSchoolPermission, IsAuthenticatedAndActive
from apps.schools.roles import Permission, Role

from .models import SubscriptionPayment, SubscriptionPaymentStatus, SubscriptionPlan
from .serializers import (
    SubscriptionPaymentCreateSerializer,
    SubscriptionPaymentReviewSerializer,
    SubscriptionPaymentSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)
from .services import (
    apply_paid_subscription_payment,
    emit_subscription_expiry_warnings,
    ensure_default_plans,
    get_school_subscription,
    reject_subscription_payment,
)


def _is_platform_admin(request) -> bool:
    user = request.user
    if getattr(user, 'is_superuser', False):
        return True
    membership = getattr(request, 'membership', None)
    return bool(membership and membership.role == Role.SUPER_ADMIN)


class PlanListView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive]
    serializer_class = SubscriptionPlanSerializer

    def get_queryset(self):
        ensure_default_plans()
        return SubscriptionPlan.objects.filter(is_active=True).prefetch_related(
            'plan_features__feature'
        )


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]
    required_permission = Permission.SCHOOL_VIEW

    def get(self, request):
        subscription = get_school_subscription(request.school)
        if subscription is None:
            return Response({'subscription': None})
        # Best-effort expiry warnings (deduped)
        try:
            emit_subscription_expiry_warnings(request.school)
        except Exception:
            pass
        return Response({'subscription': SubscriptionSerializer(subscription).data})


class SubscriptionPaymentViewSet(TenantQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = SubscriptionPaymentSerializer
    queryset = SubscriptionPayment.objects.select_related(
        'plan', 'school', 'subscription', 'submitted_by', 'reviewed_by'
    )
    filterset_fields = ('status', 'payment_method', 'plan')
    search_fields = ('transaction_reference', 'notes')
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'receipt', 'create', 'submit'):
            self.required_permission = Permission.SUBSCRIPTION_MANAGE
        elif self.action in ('approve', 'reject', 'pending'):
            # Platform admin only — checked in action; still require auth + membership
            self.required_permission = Permission.SCHOOL_VIEW
        else:
            self.required_permission = Permission.SUBSCRIPTION_MANAGE
        return [
            IsAuthenticatedAndActive(),
            HasSchoolMembership(),
            HasSchoolPermission(),
        ]

    def get_queryset(self):
        qs = super().get_queryset()
        # Platform admins can optionally see all pending across schools via pending action.
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def create(self, request, *args, **kwargs):
        return self.submit(request)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request):
        """School owner submits a manual payment request (always PENDING)."""
        serializer = SubscriptionPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data['plan_id']
        subscription = get_school_subscription(request.school)
        if subscription is None:
            raise ValidationError({'subscription': 'لا يوجد اشتراك لهذه المدرسة.'})

        amount = serializer.validated_data.get('amount') or plan.price_annual
        payment = SubscriptionPayment.objects.create(
            school=request.school,
            subscription=subscription,
            plan=plan,
            amount=amount,
            currency=plan.currency or 'USD',
            payment_method=serializer.validated_data['payment_method'],
            transaction_reference=serializer.validated_data.get('transaction_reference', ''),
            paid_at=serializer.validated_data.get('paid_at') or timezone.localdate(),
            notes=serializer.validated_data.get('notes', ''),
            status=SubscriptionPaymentStatus.PENDING,
            submitted_by=request.user,
        )
        if request.FILES.get('receipt_file'):
            payment.receipt_file = request.FILES['receipt_file']
            payment.save(update_fields=['receipt_file', 'updated_at'])

        try:
            from apps.notifications.events import on_subscription_payment_submitted

            on_subscription_payment_submitted(
                school=request.school, amount=payment.amount, currency=payment.currency
            )
        except Exception:
            pass

        return Response(
            SubscriptionPaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not _is_platform_admin(request):
            raise PermissionDenied('الموافقة متاحة لمسؤول المنصة فقط.')
        payment = self.get_object()
        if payment.status != SubscriptionPaymentStatus.PENDING:
            raise ValidationError({'status': 'يمكن اعتماد الدفعات المعلّقة فقط.'})
        review = SubscriptionPaymentReviewSerializer(data=request.data)
        review.is_valid(raise_exception=True)
        with transaction.atomic():
            apply_paid_subscription_payment(payment, reviewer=request.user)
            if review.validated_data.get('notes'):
                payment.review_notes = review.validated_data['notes']
                payment.save(update_fields=['review_notes', 'updated_at'])
        payment.refresh_from_db()
        try:
            from apps.notifications.events import on_subscription_payment_result

            on_subscription_payment_result(
                school=payment.school,
                paid=True,
                amount=payment.amount,
                currency=payment.currency,
            )
        except Exception:
            pass
        return Response(SubscriptionPaymentSerializer(payment).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not _is_platform_admin(request):
            raise PermissionDenied('الرفض متاح لمسؤول المنصة فقط.')
        payment = self.get_object()
        if payment.status != SubscriptionPaymentStatus.PENDING:
            raise ValidationError({'status': 'يمكن رفض الدفعات المعلّقة فقط.'})
        review = SubscriptionPaymentReviewSerializer(data=request.data)
        review.is_valid(raise_exception=True)
        reject_subscription_payment(
            payment,
            reviewer=request.user,
            notes=review.validated_data.get('notes', ''),
        )
        payment.refresh_from_db()
        try:
            from apps.notifications.events import on_subscription_payment_result

            on_subscription_payment_result(
                school=payment.school,
                paid=False,
                amount=payment.amount,
                currency=payment.currency,
            )
        except Exception:
            pass
        return Response(SubscriptionPaymentSerializer(payment).data)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        if payment.status != SubscriptionPaymentStatus.PAID:
            raise ValidationError({'status': 'الإيصال متاح للدفعات المدفوعة فقط.'})
        data = SubscriptionPaymentSerializer(payment).data
        data['receipt'] = {
            'platform': 'المدرسة الذكية',
            'school_name': payment.school.name,
            'school_code': payment.school.school_code,
            'plan': payment.plan.name,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'payment_method': payment.payment_method,
            'transaction_reference': payment.transaction_reference,
            'payment_date': payment.paid_at,
            'subscription_start': payment.period_start,
            'subscription_end': payment.period_end,
            'status': payment.status,
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Platform admin queue of pending payments (current school by default)."""
        if not _is_platform_admin(request):
            raise PermissionDenied('عرض الدفعات المعلّقة متاح لمسؤول المنصة فقط.')
        qs = self.filter_queryset(self.get_queryset()).filter(status=SubscriptionPaymentStatus.PENDING)
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(SubscriptionPaymentSerializer(page, many=True).data)
        return Response(SubscriptionPaymentSerializer(qs, many=True).data)
