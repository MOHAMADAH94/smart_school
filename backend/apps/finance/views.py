from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.schools.mixins import TenantQuerysetMixin
from apps.schools.roles import Permission
from apps.subscriptions.permissions import RequiresFeature

from .models import Expense, Fee, Invoice, Payment, StudentAccount
from .serializers import (
    ExpenseSerializer,
    FeeSerializer,
    InvoiceSerializer,
    PaymentSerializer,
    StudentAccountSerializer,
)


class FinanceBase(TenantQuerysetMixin):
    permission_classes = TenantQuerysetMixin.permission_classes + [RequiresFeature]
    required_feature = 'accounting'

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'summary'):
            self.required_permission = Permission.FINANCE_VIEW
        else:
            self.required_permission = Permission.FINANCE_MANAGE
        return super().get_permissions()


class FeeViewSet(FinanceBase, viewsets.ModelViewSet):
    serializer_class = FeeSerializer
    queryset = Fee.objects.select_related('student').prefetch_related('payments')
    filterset_fields = ('student', 'academic_year')
    search_fields = ('title', 'student__first_name', 'student__last_name')


class PaymentViewSet(FinanceBase, viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related('student', 'fee')
    filterset_fields = ('student', 'fee', 'payment_date')
    required_feature = 'payments'


class ExpenseViewSet(FinanceBase, viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()
    filterset_fields = ('category', 'expense_date')
    required_feature = 'expenses'


class InvoiceViewSet(FinanceBase, viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related('student', 'fee')
    filterset_fields = ('student', 'status')


class StudentAccountViewSet(FinanceBase, viewsets.ReadOnlyModelViewSet):
    serializer_class = StudentAccountSerializer
    queryset = StudentAccount.objects.select_related('student')
    filterset_fields = ('student',)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        school = self.get_school()
        total_fees = Fee.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
        paid = Payment.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
        expenses = Expense.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
        return Response(
            {
                'total_fees': total_fees,
                'paid': paid,
                'outstanding': total_fees - paid,
                'expenses': expenses,
                'revenue': paid - expenses,
            }
        )
