from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Classroom, GradeLevel
from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.services import assign_trial_subscription
from apps.teachers.models import Teacher

User = get_user_model()


class Phase2TenantIsolationTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user('ownera', 'a@ex.com', 'StrongPass123')
        self.user_b = User.objects.create_user('ownerb', 'b@ex.com', 'StrongPass123')
        self.school_a = School.objects.create(name='School A', slug='sa', school_code='SA1')
        self.school_b = School.objects.create(name='School B', slug='sb', school_code='SB1')
        SchoolMembership.objects.create(
            user=self.user_a, school=self.school_a, role=Role.SCHOOL_OWNER
        )
        SchoolMembership.objects.create(
            user=self.user_b, school=self.school_b, role=Role.SCHOOL_OWNER
        )
        assign_trial_subscription(self.school_a)
        assign_trial_subscription(self.school_b)

        grade_a = GradeLevel.objects.create(school=self.school_a, name='Grade 9', order=9)
        grade_b = GradeLevel.objects.create(school=self.school_b, name='Grade 9', order=9)
        self.class_a = Classroom.objects.create(
            school=self.school_a, grade_level=grade_a, name='Grade 9 - A'
        )
        self.class_b = Classroom.objects.create(
            school=self.school_b, grade_level=grade_b, name='Grade 9 - A'
        )
        self.student_a = Student.objects.create(
            school=self.school_a,
            student_code='A001',
            first_name='أحمد',
            last_name='علي',
            classroom=self.class_a,
        )
        self.student_b = Student.objects.create(
            school=self.school_b,
            student_code='B001',
            first_name='خالد',
            last_name='محمد',
            classroom=self.class_b,
        )
        self.teacher_b = Teacher.objects.create(
            school=self.school_b,
            employee_code='T-B1',
            first_name='سارة',
            last_name='حسن',
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

    def test_cannot_list_other_school_students(self):
        self._auth('ownera', self.school_a.id)
        response = self.client.get('/api/students/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data['results']]
        self.assertIn(self.student_a.id, ids)
        self.assertNotIn(self.student_b.id, ids)

    def test_cannot_retrieve_other_school_student(self):
        self._auth('ownera', self.school_a.id)
        response = self.client.get(f'/api/students/{self.student_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_list_other_school_teachers(self):
        self._auth('ownera', self.school_a.id)
        response = self.client.get('/api/teachers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data['results']]
        self.assertNotIn(self.teacher_b.id, ids)

    def test_create_student_in_current_school(self):
        self._auth('ownera', self.school_a.id)
        response = self.client.post(
            '/api/students/',
            {
                'student_code': 'A002',
                'first_name': 'عمر',
                'last_name': 'سعيد',
                'classroom': self.class_a.id,
                'status': 'ACTIVE',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        student = Student.objects.get(id=response.data['id'])
        self.assertEqual(student.school_id, self.school_a.id)

    def test_reject_classroom_from_other_school(self):
        self._auth('ownera', self.school_a.id)
        response = self.client.post(
            '/api/students/',
            {
                'student_code': 'A003',
                'first_name': 'نادر',
                'last_name': 'فهد',
                'classroom': self.class_b.id,
                'status': 'ACTIVE',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
