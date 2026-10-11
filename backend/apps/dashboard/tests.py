from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.attendance.models import Attendance
from apps.dashboard.insights import build_smart_center
from apps.finance.models import Fee
from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.services import assign_trial_subscription, ensure_default_plans
from apps.transport.models import Bus, BusRoute, StudentTransport

User = get_user_model()


class SmartCenterTests(APITestCase):
    def setUp(self):
        ensure_default_plans()
        self.owner = User.objects.create_user('dashowner', 'd@ex.com', 'StrongPass123')
        self.teacher = User.objects.create_user('dashteacher', 'dt@ex.com', 'StrongPass123')
        self.school = School.objects.create(name='Dash', slug='dash', school_code='DSH1')
        self.other = School.objects.create(name='OtherDash', slug='odash', school_code='DSH2')
        SchoolMembership.objects.create(user=self.owner, school=self.school, role=Role.SCHOOL_OWNER)
        SchoolMembership.objects.create(user=self.teacher, school=self.school, role=Role.TEACHER)
        assign_trial_subscription(self.school, 'professional')
        assign_trial_subscription(self.other, 'professional')
        self.student = Student.objects.create(
            school=self.school, first_name='Ali', last_name='X', student_code='DX1', status='ACTIVE'
        )

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

    def test_insights_endpoint(self):
        today = timezone.localdate()
        for i in range(3):
            Attendance.objects.create(
                school=self.school,
                student=self.student,
                date=today - timedelta(days=i),
                status='ABSENT',
            )
        self._auth(self.owner, self.school)
        response = self.client.get('/api/dashboard/insights/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = [i['code'] for i in response.data['insights']]
        self.assertIn('repeated_absences', codes)
        self.assertIn('sections', response.data)

    def test_teacher_does_not_see_finance_insights(self):
        Fee.objects.create(
            school=self.school,
            student=self.student,
            amount=Decimal('100'),
            due_date=timezone.localdate() - timedelta(days=5),
        )
        membership = SchoolMembership.objects.get(user=self.teacher, school=self.school)
        payload = build_smart_center(self.school, membership=membership)
        self.assertFalse(any(i.get('action_path') == '/finance' for i in payload['insights']))
        self.assertEqual(payload['sections'].get('financial'), {})

    def test_bus_capacity_rule(self):
        bus = Bus.objects.create(school=self.school, bus_number='03', capacity=2)
        route = BusRoute.objects.create(school=self.school, name='R1', bus=bus)
        for i in range(2):
            st = Student.objects.create(
                school=self.school,
                first_name=f'S{i}',
                last_name='T',
                student_code=f'BT{i}',
                status='ACTIVE',
            )
            StudentTransport.objects.create(
                school=self.school, student=st, bus=bus, route=route, status='ACTIVE'
            )
        membership = SchoolMembership.objects.get(user=self.owner, school=self.school)
        payload = build_smart_center(self.school, membership=membership)
        self.assertTrue(any('bus_capacity' in i['code'] for i in payload['insights']))

    def test_tenant_isolation_insights(self):
        Attendance.objects.create(
            school=self.other,
            student=Student.objects.create(
                school=self.other, first_name='O', last_name='O', student_code='OO1', status='ACTIVE'
            ),
            date=timezone.localdate(),
            status='ABSENT',
        )
        self._auth(self.owner, self.school)
        response = self.client.get('/api/dashboard/insights/')
        # School A should not reflect other school's absence count as its own today absences necessarily
        # Ensure request succeeds with school A membership only
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        att = response.data['sections'].get('attendance', {})
        # Today absence for school A is 0 unless we created one
        self.assertEqual(att.get('today_absence_count', 0), 0)
