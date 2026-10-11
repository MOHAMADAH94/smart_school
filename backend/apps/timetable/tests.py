from datetime import time

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academics.models import Classroom, GradeLevel, Subject, TeachingAssignment
from apps.parents.models import Parent, StudentParent
from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.models import Feature, PlanFeature, SubscriptionPlan
from apps.subscriptions.services import assign_trial_subscription, ensure_default_plans
from apps.teachers.models import Teacher
from apps.timetable.models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableStatus,
    WeeklySubjectRequirement,
)
from apps.timetable.services import generate_timetable, validate_timetable

User = get_user_model()


class TimetableBaseTest(APITestCase):
    def setUp(self):
        ensure_default_plans()
        self.owner = User.objects.create_user('tt_owner', 'o@ex.com', 'StrongPass123')
        self.teacher_user = User.objects.create_user('tt_teacher', 't@ex.com', 'StrongPass123')
        self.parent_user = User.objects.create_user('tt_parent', 'p@ex.com', 'StrongPass123')
        self.other_owner = User.objects.create_user('tt_other', 'x@ex.com', 'StrongPass123')

        self.school = School.objects.create(name='TT School', slug='tt-school', school_code='TT1')
        self.school_b = School.objects.create(name='TT B', slug='tt-b', school_code='TT2')
        SchoolMembership.objects.create(user=self.owner, school=self.school, role=Role.SCHOOL_OWNER)
        SchoolMembership.objects.create(
            user=self.teacher_user, school=self.school, role=Role.TEACHER
        )
        SchoolMembership.objects.create(user=self.parent_user, school=self.school, role=Role.PARENT)
        SchoolMembership.objects.create(
            user=self.other_owner, school=self.school_b, role=Role.SCHOOL_OWNER
        )
        assign_trial_subscription(self.school)
        assign_trial_subscription(self.school_b)

        self.grade = GradeLevel.objects.create(school=self.school, name='G7', order=7)
        self.class_a = Classroom.objects.create(
            school=self.school, grade_level=self.grade, name='7-A', section='A'
        )
        self.class_b = Classroom.objects.create(
            school=self.school, grade_level=self.grade, name='7-B', section='B'
        )
        self.math = Subject.objects.create(school=self.school, name='Mathematics', code='MATH')
        self.arabic = Subject.objects.create(school=self.school, name='Arabic', code='AR')

        self.teacher = Teacher.objects.create(
            school=self.school,
            user=self.teacher_user,
            employee_code='T1',
            first_name='Ahmad',
            last_name='Teacher',
        )
        self.teacher2 = Teacher.objects.create(
            school=self.school,
            employee_code='T2',
            first_name='Sara',
            last_name='Teacher',
        )
        self.ta_math_a = TeachingAssignment.objects.create(
            school=self.school,
            teacher=self.teacher,
            subject=self.math,
            classroom=self.class_a,
        )
        self.ta_math_b = TeachingAssignment.objects.create(
            school=self.school,
            teacher=self.teacher,
            subject=self.math,
            classroom=self.class_b,
        )
        self.ta_ar_a = TeachingAssignment.objects.create(
            school=self.school,
            teacher=self.teacher2,
            subject=self.arabic,
            classroom=self.class_a,
        )

        self.timetable = Timetable.objects.create(
            school=self.school,
            name='Main',
            academic_year='2025-2026',
            working_days=[0, 1, 2, 3, 4],
            status=TimetableStatus.DRAFT,
        )
        self.p1 = TimetablePeriod.objects.create(
            timetable=self.timetable,
            period_number=1,
            label='الحصة 1',
            start_time=time(8, 0),
            end_time=time(8, 45),
        )
        self.p2 = TimetablePeriod.objects.create(
            timetable=self.timetable,
            period_number=2,
            label='الحصة 2',
            start_time=time(8, 45),
            end_time=time(9, 30),
        )
        WeeklySubjectRequirement.objects.create(
            school=self.school,
            timetable=self.timetable,
            classroom=self.class_a,
            subject=self.math,
            teaching_assignment=self.ta_math_a,
            lessons_per_week=2,
            max_lessons_per_day=1,
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


class TimetableConflictTests(TimetableBaseTest):
    def test_class_conflict_rejected(self):
        self._auth(self.owner, self.school)
        payload = {
            'timetable': self.timetable.id,
            'day': 0,
            'period': self.p1.id,
            'classroom': self.class_a.id,
            'subject': self.math.id,
            'teaching_assignment': self.ta_math_a.id,
        }
        r1 = self.client.post('/api/timetables/entries/', payload, format='json')
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        payload2 = {
            **payload,
            'subject': self.arabic.id,
            'teaching_assignment': self.ta_ar_a.id,
        }
        r2 = self.client.post('/api/timetables/entries/', payload2, format='json')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_conflict_rejected(self):
        self._auth(self.owner, self.school)
        self.client.post(
            '/api/timetables/entries/',
            {
                'timetable': self.timetable.id,
                'day': 0,
                'period': self.p1.id,
                'classroom': self.class_a.id,
                'subject': self.math.id,
                'teaching_assignment': self.ta_math_a.id,
            },
            format='json',
        )
        r = self.client.post(
            '/api/timetables/entries/',
            {
                'timetable': self.timetable.id,
                'day': 0,
                'period': self.p1.id,
                'classroom': self.class_b.id,
                'subject': self.math.id,
                'teaching_assignment': self.ta_math_b.id,
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_assignment_rejected(self):
        self._auth(self.owner, self.school)
        r = self.client.post(
            '/api/timetables/entries/',
            {
                'timetable': self.timetable.id,
                'day': 0,
                'period': self.p1.id,
                'classroom': self.class_a.id,
                'subject': self.arabic.id,
                'teaching_assignment': self.ta_math_a.id,
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_teacher_availability_blocks_slot(self):
        TeacherAvailability.objects.create(
            school=self.school,
            teacher=self.teacher,
            day=0,
            period_number=1,
            is_available=False,
        )
        self._auth(self.owner, self.school)
        r = self.client.post(
            '/api/timetables/entries/',
            {
                'timetable': self.timetable.id,
                'day': 0,
                'period': self.p1.id,
                'classroom': self.class_a.id,
                'subject': self.math.id,
                'teaching_assignment': self.ta_math_a.id,
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weekly_requirement_incomplete_warning(self):
        TimetableEntry.objects.create(
            school=self.school,
            timetable=self.timetable,
            day=0,
            period=self.p1,
            classroom=self.class_a,
            subject=self.math,
            teaching_assignment=self.ta_math_a,
        )
        report = validate_timetable(self.timetable)
        codes = [w['code'] for w in report['warnings']]
        self.assertIn('requirement_incomplete', codes)


class TimetablePermissionTests(TimetableBaseTest):
    def test_tenant_isolation(self):
        self._auth(self.other_owner, self.school_b)
        r = self.client.get('/api/timetables/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in r.data['results']]
        self.assertNotIn(self.timetable.id, ids)

    def test_teacher_cannot_modify(self):
        self._auth(self.teacher_user, self.school)
        r = self.client.post(
            '/api/timetables/',
            {'name': 'Hack', 'academic_year': '2025-2026'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_view_own(self):
        TimetableEntry.objects.create(
            school=self.school,
            timetable=self.timetable,
            day=0,
            period=self.p1,
            classroom=self.class_a,
            subject=self.math,
            teaching_assignment=self.ta_math_a,
        )
        self.timetable.status = TimetableStatus.PUBLISHED
        self.timetable.save(update_fields=['status'])
        self._auth(self.teacher_user, self.school)
        r = self.client.get('/api/timetables/my/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data['entries']), 1)

    def test_parent_child_only(self):
        parent = Parent.objects.create(
            school=self.school, user=self.parent_user, name='Parent', phone='1'
        )
        student = Student.objects.create(
            school=self.school,
            student_code='S1',
            first_name='Child',
            last_name='A',
            classroom=self.class_a,
        )
        other = Student.objects.create(
            school=self.school,
            student_code='S2',
            first_name='Other',
            last_name='B',
            classroom=self.class_b,
        )
        StudentParent.objects.create(school=self.school, parent=parent, student=student)
        self.timetable.status = TimetableStatus.PUBLISHED
        self.timetable.save(update_fields=['status'])
        self._auth(self.parent_user, self.school)
        ok = self.client.get(f'/api/timetables/child/{student.id}/')
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        bad = self.client.get(f'/api/timetables/child/{other.id}/')
        self.assertEqual(bad.status_code, status.HTTP_403_FORBIDDEN)

    def test_publish_requires_manage(self):
        self._auth(self.teacher_user, self.school)
        r = self.client.post(f'/api/timetables/{self.timetable.id}/publish/')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_feature_gate(self):
        ensure_default_plans()
        feature = Feature.objects.get(code='timetable')
        plan = SubscriptionPlan.objects.get(code='professional')
        PlanFeature.objects.filter(plan=plan, feature=feature).update(is_enabled=False)
        self._auth(self.owner, self.school)
        r = self.client.get('/api/timetables/')
        self.assertIn(r.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_402_PAYMENT_REQUIRED})
        PlanFeature.objects.filter(plan=plan, feature=feature).update(is_enabled=True)

    def test_owner_can_publish(self):
        TimetableEntry.objects.create(
            school=self.school,
            timetable=self.timetable,
            day=0,
            period=self.p1,
            classroom=self.class_a,
            subject=self.math,
            teaching_assignment=self.ta_math_a,
        )
        TimetableEntry.objects.create(
            school=self.school,
            timetable=self.timetable,
            day=1,
            period=self.p1,
            classroom=self.class_a,
            subject=self.math,
            teaching_assignment=self.ta_math_a,
        )
        self._auth(self.owner, self.school)
        r = self.client.post(f'/api/timetables/{self.timetable.id}/publish/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.timetable.refresh_from_db()
        self.assertEqual(self.timetable.status, TimetableStatus.PUBLISHED)


class TimetableGeneratorTests(TimetableBaseTest):
    def test_generate_fills_requirements(self):
        result = generate_timetable(self.timetable, replace_existing=True)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['proposed']), 2)
