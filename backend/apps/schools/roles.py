"""Role and permission constants for the multi-tenant school platform."""

from __future__ import annotations


class Role:
    SUPER_ADMIN = 'SUPER_ADMIN'
    SCHOOL_OWNER = 'SCHOOL_OWNER'
    SCHOOL_ADMIN = 'SCHOOL_ADMIN'
    ACCOUNTANT = 'ACCOUNTANT'
    TEACHER = 'TEACHER'
    PARENT = 'PARENT'
    STUDENT = 'STUDENT'

    CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (SCHOOL_OWNER, 'School Owner'),
        (SCHOOL_ADMIN, 'School Admin'),
        (ACCOUNTANT, 'Accountant'),
        (TEACHER, 'Teacher'),
        (PARENT, 'Parent'),
        (STUDENT, 'Student'),
    ]

    ALL = {c[0] for c in CHOICES}


class Permission:
    # School
    SCHOOL_VIEW = 'school.view'
    SCHOOL_MANAGE = 'school.manage'
    MEMBERSHIP_MANAGE = 'membership.manage'

    # Academic core
    STUDENTS_VIEW = 'students.view'
    STUDENTS_MANAGE = 'students.manage'
    TEACHERS_VIEW = 'teachers.view'
    TEACHERS_MANAGE = 'teachers.manage'
    PARENTS_VIEW = 'parents.view'
    PARENTS_MANAGE = 'parents.manage'
    CLASSES_VIEW = 'classes.view'
    CLASSES_MANAGE = 'classes.manage'
    SUBJECTS_VIEW = 'subjects.view'
    SUBJECTS_MANAGE = 'subjects.manage'

    # Operations
    ATTENDANCE_VIEW = 'attendance.view'
    ATTENDANCE_MANAGE = 'attendance.manage'
    GRADES_VIEW = 'grades.view'
    GRADES_MANAGE = 'grades.manage'
    TRANSPORT_VIEW = 'transport.view'
    TRANSPORT_MANAGE = 'transport.manage'

    # Professional
    FINANCE_VIEW = 'finance.view'
    FINANCE_MANAGE = 'finance.manage'
    NOTIFICATIONS_VIEW = 'notifications.view'
    NOTIFICATIONS_MANAGE = 'notifications.manage'
    REPORTS_VIEW = 'reports.view'
    SUBSCRIPTION_MANAGE = 'subscription.manage'
    DASHBOARD_VIEW = 'dashboard.view'
    TIMETABLE_VIEW = 'timetable.view'
    TIMETABLE_MANAGE = 'timetable.manage'


ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.SUPER_ADMIN: {'*'},
    Role.SCHOOL_OWNER: {
        Permission.SCHOOL_VIEW,
        Permission.SCHOOL_MANAGE,
        Permission.MEMBERSHIP_MANAGE,
        Permission.STUDENTS_VIEW,
        Permission.STUDENTS_MANAGE,
        Permission.TEACHERS_VIEW,
        Permission.TEACHERS_MANAGE,
        Permission.PARENTS_VIEW,
        Permission.PARENTS_MANAGE,
        Permission.CLASSES_VIEW,
        Permission.CLASSES_MANAGE,
        Permission.SUBJECTS_VIEW,
        Permission.SUBJECTS_MANAGE,
        Permission.ATTENDANCE_VIEW,
        Permission.ATTENDANCE_MANAGE,
        Permission.GRADES_VIEW,
        Permission.GRADES_MANAGE,
        Permission.TRANSPORT_VIEW,
        Permission.TRANSPORT_MANAGE,
        Permission.FINANCE_VIEW,
        Permission.FINANCE_MANAGE,
        Permission.NOTIFICATIONS_VIEW,
        Permission.NOTIFICATIONS_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.SUBSCRIPTION_MANAGE,
        Permission.DASHBOARD_VIEW,
        Permission.TIMETABLE_VIEW,
        Permission.TIMETABLE_MANAGE,
    },
    Role.SCHOOL_ADMIN: {
        Permission.SCHOOL_VIEW,
        Permission.MEMBERSHIP_MANAGE,
        Permission.STUDENTS_VIEW,
        Permission.STUDENTS_MANAGE,
        Permission.TEACHERS_VIEW,
        Permission.TEACHERS_MANAGE,
        Permission.PARENTS_VIEW,
        Permission.PARENTS_MANAGE,
        Permission.CLASSES_VIEW,
        Permission.CLASSES_MANAGE,
        Permission.SUBJECTS_VIEW,
        Permission.SUBJECTS_MANAGE,
        Permission.ATTENDANCE_VIEW,
        Permission.ATTENDANCE_MANAGE,
        Permission.GRADES_VIEW,
        Permission.GRADES_MANAGE,
        Permission.TRANSPORT_VIEW,
        Permission.TRANSPORT_MANAGE,
        Permission.NOTIFICATIONS_VIEW,
        Permission.NOTIFICATIONS_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.DASHBOARD_VIEW,
        Permission.TIMETABLE_VIEW,
        Permission.TIMETABLE_MANAGE,
    },
    Role.ACCOUNTANT: {
        Permission.SCHOOL_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.PARENTS_VIEW,
        Permission.FINANCE_VIEW,
        Permission.FINANCE_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.DASHBOARD_VIEW,
        Permission.NOTIFICATIONS_VIEW,
    },
    Role.TEACHER: {
        Permission.SCHOOL_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.CLASSES_VIEW,
        Permission.SUBJECTS_VIEW,
        Permission.ATTENDANCE_VIEW,
        Permission.ATTENDANCE_MANAGE,
        Permission.GRADES_VIEW,
        Permission.GRADES_MANAGE,
        Permission.PARENTS_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.TIMETABLE_VIEW,
    },
    Role.PARENT: {
        Permission.SCHOOL_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.ATTENDANCE_VIEW,
        Permission.GRADES_VIEW,
        Permission.TRANSPORT_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.TIMETABLE_VIEW,
    },
    Role.STUDENT: {
        Permission.SCHOOL_VIEW,
        Permission.STUDENTS_VIEW,
        Permission.ATTENDANCE_VIEW,
        Permission.GRADES_VIEW,
        Permission.TRANSPORT_VIEW,
        Permission.NOTIFICATIONS_VIEW,
        Permission.TIMETABLE_VIEW,
    },
}


def permissions_for_role(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def role_has_permission(role: str, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return '*' in perms or permission in perms
