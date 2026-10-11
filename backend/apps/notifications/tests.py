from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.events import notify_parent_users_for_student, on_student_absent
from apps.notifications.models import Notification, NotificationAudience, NotificationPreference, PreferenceCategory
from apps.parents.models import Parent, StudentParent
from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.services import assign_trial_subscription, ensure_default_plans

User = get_user_model()


class NotificationIsolationTests(APITestCase):
    def setUp(self):
        ensure_default_plans()
        self.school_a = School.objects.create(name='A', slug='na', school_code='NA1')
        self.school_b = School.objects.create(name='B', slug='nb', school_code='NB1')
        assign_trial_subscription(self.school_a, 'professional')
        assign_trial_subscription(self.school_b, 'professional')

        self.parent_a = User.objects.create_user('parenta', 'pa@ex.com', 'StrongPass123')
        self.parent_b = User.objects.create_user('parentb', 'pb@ex.com', 'StrongPass123')
        self.owner_a = User.objects.create_user('ownera', 'oa@ex.com', 'StrongPass123')

        SchoolMembership.objects.create(user=self.parent_a, school=self.school_a, role=Role.PARENT)
        SchoolMembership.objects.create(user=self.parent_b, school=self.school_a, role=Role.PARENT)
        SchoolMembership.objects.create(user=self.owner_a, school=self.school_a, role=Role.SCHOOL_OWNER)
        SchoolMembership.objects.create(user=self.owner_a, school=self.school_b, role=Role.SCHOOL_OWNER)

        self.student_a = Student.objects.create(
            school=self.school_a, first_name='Ahmed', last_name='A', student_code='SA1', status='ACTIVE'
        )
        self.student_b = Student.objects.create(
            school=self.school_a, first_name='Sara', last_name='B', student_code='SB1', status='ACTIVE'
        )
        pa = Parent.objects.create(school=self.school_a, user=self.parent_a, name='Parent A')
        pb = Parent.objects.create(school=self.school_a, user=self.parent_b, name='Parent B')
        StudentParent.objects.create(school=self.school_a, parent=pa, student=self.student_a)
        StudentParent.objects.create(school=self.school_a, parent=pb, student=self.student_b)

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

    def test_parent_only_sees_own_child_user_notifications(self):
        notify_parent_users_for_student(
            school=self.school_a,
            student=self.student_a,
            title='Ahmed absent',
            body='x',
            type='ATTENDANCE',
        )
        notify_parent_users_for_student(
            school=self.school_a,
            student=self.student_b,
            title='Sara absent',
            body='y',
            type='ATTENDANCE',
        )
        self._auth(self.parent_a, self.school_a)
        response = self.client.get('/api/notifications/')
        rows = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        titles = [n['title'] for n in rows]
        self.assertIn('Ahmed absent', titles)
        self.assertNotIn('Sara absent', titles)

    def test_tenant_isolation_notifications(self):
        Notification.objects.create(
            school=self.school_b,
            title='Secret B',
            body='b',
            audience=NotificationAudience.ALL,
        )
        self._auth(self.owner_a, self.school_a)
        response = self.client.get('/api/notifications/')
        rows = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        titles = [n['title'] for n in rows]
        self.assertNotIn('Secret B', titles)

    def test_absence_event_dedupe(self):
        from django.utils import timezone

        d = timezone.localdate()
        c1 = on_student_absent(school=self.school_a, student=self.student_a, date=d)
        c2 = on_student_absent(school=self.school_a, student=self.student_a, date=d)
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 0)

    def test_preferences_cannot_disable_announcements(self):
        self._auth(self.parent_a, self.school_a)
        response = self.client.put(
            '/api/notifications/preferences/',
            {'preferences': [{'category': 'ANNOUNCEMENTS', 'enabled': False}]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pref = NotificationPreference.objects.get(
            school=self.school_a, user=self.parent_a, category=PreferenceCategory.ANNOUNCEMENTS
        )
        self.assertTrue(pref.enabled)

    def test_unread_count(self):
        Notification.objects.create(
            school=self.school_a,
            user=self.parent_a,
            audience=NotificationAudience.USER,
            title='Hi',
            body='',
        )
        self._auth(self.parent_a, self.school_a)
        response = self.client.get('/api/notifications/unread_count/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_mark_all_read_clears_unread(self):
        Notification.objects.create(
            school=self.school_a,
            audience=NotificationAudience.ALL,
            title='Broadcast',
            body='',
        )
        Notification.objects.create(
            school=self.school_a,
            user=self.parent_a,
            audience=NotificationAudience.USER,
            title='Personal',
            body='',
        )
        self._auth(self.parent_a, self.school_a)
        before = self.client.get('/api/notifications/unread_count/').data['count']
        self.assertGreaterEqual(before, 1)
        marked = self.client.post('/api/notifications/mark_all_read/')
        self.assertEqual(marked.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(marked.data.get('marked', 0), 1)
        after = self.client.get('/api/notifications/unread_count/').data['count']
        self.assertEqual(after, 0)
        rows = self.client.get('/api/notifications/').data['results']
        self.assertTrue(all(n['is_read'] for n in rows))
