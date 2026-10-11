from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.subscriptions.models import (
    SubscriptionPayment,
    SubscriptionPaymentStatus,
    SubscriptionPlan,
    SubscriptionStatus,
)
from apps.subscriptions.services import (
    apply_paid_subscription_payment,
    assign_trial_subscription,
    compute_renewal_period,
    emit_subscription_expiry_warnings,
    ensure_default_plans,
    reject_subscription_payment,
)
from apps.subscriptions.models import NotificationEventLog

User = get_user_model()


class SubscriptionPaymentWorkflowTests(APITestCase):
    def setUp(self):
        ensure_default_plans()
        self.owner = User.objects.create_user('payowner', 'o@ex.com', 'StrongPass123')
        self.admin = User.objects.create_superuser('payadmin', 'a@ex.com', 'StrongPass123')
        self.school = School.objects.create(name='Pay School', slug='pay-school', school_code='PAY1')
        self.other = School.objects.create(name='Other School', slug='other-pay', school_code='PAY2')
        SchoolMembership.objects.create(user=self.owner, school=self.school, role=Role.SCHOOL_OWNER)
        SchoolMembership.objects.create(user=self.admin, school=self.school, role=Role.SUPER_ADMIN)
        SchoolMembership.objects.create(user=self.admin, school=self.other, role=Role.SUPER_ADMIN)
        self.subscription = assign_trial_subscription(self.school, plan_code='professional')
        assign_trial_subscription(self.other, plan_code='basic')
        self.plan = SubscriptionPlan.objects.get(code='professional')

    def _auth(self, user, school):
        token = self.client.post(
            reverse('auth-login'),
            {'username': user.username, 'password': 'StrongPass123'},
            format='json',
        ).data['access']
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_SCHOOL_ID=str(school.id),
        )

    def test_owner_submits_pending_cannot_self_approve(self):
        self._auth(self.owner, self.school)
        response = self.client.post(
            '/api/subscriptions/payments/submit/',
            {
                'plan_id': self.plan.id,
                'payment_method': 'BANK_TRANSFER',
                'transaction_reference': 'TX-100',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], SubscriptionPaymentStatus.PENDING)
        payment_id = response.data['id']

        approve = self.client.post(f'/api/subscriptions/payments/{payment_id}/approve/', {}, format='json')
        self.assertEqual(approve.status_code, status.HTTP_403_FORBIDDEN)

    def test_platform_admin_approve_activates(self):
        payment = SubscriptionPayment.objects.create(
            school=self.school,
            subscription=self.subscription,
            plan=self.plan,
            amount=self.plan.price_annual,
            currency='USD',
            payment_method='BANK_TRANSFER',
            transaction_reference='TX-200',
            status=SubscriptionPaymentStatus.PENDING,
            paid_at=timezone.localdate(),
            submitted_by=self.owner,
        )
        self._auth(self.admin, self.school)
        response = self.client.post(f'/api/subscriptions/payments/{payment.id}/approve/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.subscription.refresh_from_db()
        self.assertEqual(payment.status, SubscriptionPaymentStatus.PAID)
        self.assertEqual(self.subscription.status, SubscriptionStatus.ACTIVE)

    def test_reject_payment(self):
        payment = SubscriptionPayment.objects.create(
            school=self.school,
            subscription=self.subscription,
            plan=self.plan,
            amount=Decimal('999.00'),
            currency='USD',
            payment_method='CASH',
            status=SubscriptionPaymentStatus.PENDING,
            submitted_by=self.owner,
        )
        reject_subscription_payment(payment, reviewer=self.admin, notes='invalid')
        payment.refresh_from_db()
        self.assertEqual(payment.status, SubscriptionPaymentStatus.REJECTED)

    def test_renewal_while_active_extends_from_end_date(self):
        today = timezone.localdate()
        self.subscription.status = SubscriptionStatus.ACTIVE
        self.subscription.start_date = today - timedelta(days=200)
        self.subscription.end_date = today + timedelta(days=30)
        self.subscription.save()
        paid_on = today
        start, end = compute_renewal_period(self.subscription, paid_on=paid_on)
        self.assertEqual(start, self.subscription.end_date)
        self.assertEqual(end, self.subscription.end_date + timedelta(days=365))

        payment = SubscriptionPayment.objects.create(
            school=self.school,
            subscription=self.subscription,
            plan=self.plan,
            amount=Decimal('999'),
            paid_at=paid_on,
            status=SubscriptionPaymentStatus.PENDING,
        )
        original_start = self.subscription.start_date
        apply_paid_subscription_payment(payment, reviewer=self.admin)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.start_date, original_start)
        self.assertEqual(self.subscription.end_date, end)

    def test_renewal_after_expiry_starts_from_payment_date(self):
        today = timezone.localdate()
        self.subscription.status = SubscriptionStatus.EXPIRED
        self.subscription.end_date = today - timedelta(days=10)
        self.subscription.save()
        paid_on = today
        start, end = compute_renewal_period(self.subscription, paid_on=paid_on)
        self.assertEqual(start, paid_on)
        self.assertEqual(end, paid_on + timedelta(days=365))

    def test_tenant_isolation_payments(self):
        payment = SubscriptionPayment.objects.create(
            school=self.other,
            subscription=self.other.subscription,
            plan=SubscriptionPlan.objects.get(code='basic'),
            amount=Decimal('100'),
            status=SubscriptionPaymentStatus.PENDING,
        )
        self._auth(self.owner, self.school)
        response = self.client.get('/api/subscriptions/payments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        ids = [row['id'] for row in rows]
        self.assertNotIn(payment.id, ids)
        detail = self.client.get(f'/api/subscriptions/payments/{payment.id}/')
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_expiry_warnings_deduped(self):
        self.subscription.end_date = timezone.localdate() + timedelta(days=30)
        self.subscription.status = SubscriptionStatus.ACTIVE
        self.subscription.save()
        first = emit_subscription_expiry_warnings(self.school)
        second = emit_subscription_expiry_warnings(self.school)
        self.assertTrue(any('30' in k for k in first))
        self.assertEqual(second, [])
        self.assertEqual(
            NotificationEventLog.objects.filter(
                school=self.school, event_key=f'subscription_expiry:{self.school.id}:30'
            ).count(),
            1,
        )

    def test_subscription_me_includes_display_fields(self):
        self._auth(self.owner, self.school)
        response = self.client.get('/api/subscriptions/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sub = response.data['subscription']
        self.assertIn('days_remaining', sub)
        self.assertIn('display_status', sub)
        self.assertIn('enabled_features', sub)
