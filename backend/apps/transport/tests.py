from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.services import assign_trial_subscription
from apps.transport.models import Bus, BusDriver, BusRoute, StudentTransport

User = get_user_model()


class TransportIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user('ta', 'ta@ex.com', 'StrongPass123')
        self.user_b = User.objects.create_user('tb', 'tb@ex.com', 'StrongPass123')
        self.school_a = School.objects.create(name='TA', slug='ta', school_code='TA1')
        self.school_b = School.objects.create(name='TB', slug='tb', school_code='TB1')
        SchoolMembership.objects.create(user=self.user_a, school=self.school_a, role=Role.SCHOOL_OWNER)
        SchoolMembership.objects.create(user=self.user_b, school=self.school_b, role=Role.SCHOOL_OWNER)
        assign_trial_subscription(self.school_a)
        assign_trial_subscription(self.school_b)

        self.driver_b = BusDriver.objects.create(school=self.school_b, name='Driver B')
        self.bus_b = Bus.objects.create(
            school=self.school_b, bus_number='#99', capacity=10, driver=self.driver_b
        )
        self.route_b = BusRoute.objects.create(
            school=self.school_b, name='Route B', bus=self.bus_b, driver=self.driver_b
        )
        self.student_b = Student.objects.create(
            school=self.school_b, student_code='SB1', first_name='B', last_name='Student'
        )
        StudentTransport.objects.create(
            school=self.school_b,
            student=self.student_b,
            bus=self.bus_b,
            route=self.route_b,
        )

    def _auth(self, username, school_id):
        token = self.client.post(
            reverse('auth-login'),
            {'username': username, 'password': 'StrongPass123'},
            format='json',
        ).data['access']
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_SCHOOL_ID=str(school_id),
        )

    def test_cannot_see_other_school_buses(self):
        self._auth('ta', self.school_a.id)
        response = self.client.get('/api/transport/buses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data['results']]
        self.assertNotIn(self.bus_b.id, ids)

    def test_cannot_assign_cross_tenant_transport(self):
        self._auth('ta', self.school_a.id)
        student_a = Student.objects.create(
            school=self.school_a, student_code='SA1', first_name='A', last_name='Student'
        )
        response = self.client.post(
            '/api/transport/assignments/',
            {
                'student': student_a.id,
                'bus': self.bus_b.id,
                'route': self.route_b.id,
                'status': 'ACTIVE',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
