from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.subscriptions.models import Subscription

User = get_user_model()


class AuthenticationTests(APITestCase):
    def test_user_can_register(self):
        url = reverse('auth-register')
        payload = {
            'username': 'owner1',
            'email': 'owner1@example.com',
            'password': 'StrongPass123',
            'first_name': 'أحمد',
            'last_name': 'علي',
            'phone': '0500000001',
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='owner1').exists())
        user = User.objects.get(username='owner1')
        self.assertTrue(user.check_password('StrongPass123'))

    def test_user_can_login(self):
        User.objects.create_user(
            username='owner2',
            email='owner2@example.com',
            password='StrongPass123',
        )
        url = reverse('auth-login')
        response = self.client.post(
            url,
            {'username': 'owner2', 'password': 'StrongPass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['username'], 'owner2')


class SchoolOnboardingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='schoolowner',
            email='schoolowner@example.com',
            password='StrongPass123',
        )
        login = self.client.post(
            reverse('auth-login'),
            {'username': 'schoolowner', 'password': 'StrongPass123'},
            format='json',
        )
        self.token = login.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_create_school_creates_owner_membership_and_trial(self):
        response = self.client.post(
            reverse('schools-create'),
            {
                'name': 'مدرسة النور',
                'city': 'الرياض',
                'country': 'السعودية',
                'academic_year': '2025-2026',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        school = School.objects.get(name='مدرسة النور')
        membership = SchoolMembership.objects.get(user=self.user, school=school)
        self.assertEqual(membership.role, Role.SCHOOL_OWNER)
        self.assertTrue(Subscription.objects.filter(school=school).exists())
        self.assertTrue(school.school_code)

    def test_me_returns_memberships(self):
        school = School.objects.create(name='Test School', slug='test-school', school_code='TST001')
        SchoolMembership.objects.create(
            user=self.user,
            school=school,
            role=Role.SCHOOL_OWNER,
        )
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['memberships']), 1)


class TenantIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', email='a@example.com', password='StrongPass123'
        )
        self.user_b = User.objects.create_user(
            username='userb', email='b@example.com', password='StrongPass123'
        )
        self.school_a = School.objects.create(
            name='School A', slug='school-a', school_code='SCHA001'
        )
        self.school_b = School.objects.create(
            name='School B', slug='school-b', school_code='SCHB001'
        )
        SchoolMembership.objects.create(
            user=self.user_a, school=self.school_a, role=Role.SCHOOL_OWNER
        )
        SchoolMembership.objects.create(
            user=self.user_b, school=self.school_b, role=Role.SCHOOL_OWNER
        )

    def _auth(self, username: str) -> str:
        response = self.client.post(
            reverse('auth-login'),
            {'username': username, 'password': 'StrongPass123'},
            format='json',
        )
        return response.data['access']

    def test_user_cannot_select_foreign_school_via_header(self):
        token = self._auth('usera')
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_SCHOOL_ID=str(self.school_b.id),
        )
        response = self.client.get(reverse('schools-current'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['has_school'])

    def test_user_can_access_own_school_context(self):
        token = self._auth('usera')
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_SCHOOL_ID=str(self.school_a.id),
        )
        response = self.client.get(reverse('schools-current'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_school'])
        self.assertEqual(response.data['school']['id'], self.school_a.id)

    def test_permissions_included_for_owner(self):
        token = self._auth('usera')
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_SCHOOL_ID=str(self.school_a.id),
        )
        response = self.client.get(reverse('schools-current'))
        self.assertIn('students.manage', response.data['permissions'])
        self.assertIn('finance.manage', response.data['permissions'])
