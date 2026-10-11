from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academics.models import Classroom, GradeLevel, Subject, TeachingAssignment
from apps.attendance.models import Attendance
from apps.finance.models import Expense, Fee, Invoice, Payment, StudentAccount
from apps.grades.models import AcademicTerm, Assessment, AssessmentType, Grade
from apps.notifications.models import Notification, NotificationAudience
from apps.parents.models import Parent, Relationship, StudentParent
from apps.schools.models import School, SchoolMembership
from apps.schools.roles import Role
from apps.students.models import Student
from apps.subscriptions.services import assign_trial_subscription, ensure_default_plans
from apps.teachers.models import Teacher
from apps.timetable.models import (
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableStatus,
    WeeklySubjectRequirement,
)
from apps.timetable.services import apply_generated_entries, generate_timetable, publish_timetable
from apps.transport.models import Bus, BusDriver, BusRoute, StudentTransport

User = get_user_model()

GRADE_NAMES = [
    'الصف الأول',
    'الصف الثاني',
    'الصف الثالث',
    'الصف الرابع',
    'الصف الخامس',
    'الصف السادس',
]

SUBJECT_DEFS = [
    ('MATH', 'رياضيات', 5, 2),
    ('AR', 'لغة عربية', 5, 2),
    ('EN', 'لغة إنجليزية', 4, 2),
    ('SCI', 'علوم', 3, 1),
    ('ISLAM', 'تربية إسلامية', 2, 1),
    ('SOC', 'اجتماعيات', 2, 1),
    ('PE', 'تربية بدنية', 2, 1),
]

TEACHER_DEFS = [
    # first_name, last_name, specialization, subject_code, username or None
    ('نورة', 'العلي', 'رياضيات', 'MATH', 'demo_teacher'),
    ('منال', 'القحطاني', 'رياضيات', 'MATH', 'teacher_math2'),
    ('إبراهيم', 'النهدي', 'رياضيات', 'MATH', 'teacher_math3'),
    ('ليلى', 'حسن', 'لغة عربية', 'AR', 'teacher_ar'),
    ('أحمد', 'الزهراني', 'لغة عربية', 'AR', 'teacher_ar2'),
    ('نوال', 'الشهري', 'لغة عربية', 'AR', 'teacher_ar3'),
    ('فهد', 'الشمري', 'لغة إنجليزية', 'EN', 'teacher_en'),
    ('هند', 'الغامدي', 'لغة إنجليزية', 'EN', 'teacher_en2'),
    ('خالد', 'سعيد', 'علوم', 'SCI', 'teacher_sci'),
    ('راكان', 'العنزي', 'علوم', 'SCI', 'teacher_sci2'),
    ('سارة', 'الدوسري', 'تربية إسلامية', 'ISLAM', 'teacher_islam'),
    ('ريم', 'السبيعي', 'تربية إسلامية', 'ISLAM', None),
    ('ماجد', 'العتيبي', 'اجتماعيات', 'SOC', 'teacher_soc'),
    ('يوسف', 'الحربي', 'تربية بدنية', 'PE', 'teacher_pe'),
]

BOY_NAMES = [
    ('أحمد', 'محمد', 'علي'),
    ('محمد', 'سعيد', 'الحربي'),
    ('خالد', 'فهد', 'القحطاني'),
    ('علي', 'عمر', 'الدوسري'),
    ('عمر', 'ياسر', 'الشهري'),
    ('يوسف', 'ناصر', 'الزهراني'),
    ('فيصل', 'تركي', 'العنزي'),
    ('سلمان', 'بندر', 'المطيري'),
    ('عبدالله', 'ماجد', 'العتيبي'),
    ('زياد', 'سعد', 'الغامدي'),
]
GIRL_NAMES = [
    ('سارة', 'عبدالله', 'المطيري'),
    ('نورة', 'خالد', 'العتيبي'),
    ('ريم', 'سلمان', 'الغامدي'),
    ('لينا', 'ماجد', 'الحربي'),
    ('جود', 'بندر', 'السبيعي'),
    ('لمى', 'فيصل', 'الشمري'),
    ('دانة', 'وليد', 'القحطاني'),
    ('هيا', 'طلال', 'الدوسري'),
    ('غادة', 'ناصر', 'الزهراني'),
    ('ملك', 'سعود', 'العنزي'),
]

STUDENTS_PER_CLASS = 10


class Command(BaseCommand):
    help = 'Seed a fully usable demo school (grades 1–6, teachers, students, timetable)'

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_default_plans()
        today = timezone.localdate()

        admin_user, _ = User.objects.get_or_create(
            username='demo_admin',
            defaults={
                'email': 'demo@smartschool.test',
                'first_name': 'مدير',
                'last_name': 'التجريبي',
                'phone': '0500000000',
            },
        )
        admin_user.set_password('Demo@12345')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.first_name = 'مدير'
        admin_user.last_name = 'التجريبي'
        admin_user.email = 'demo@smartschool.test'
        admin_user.phone = '0500000000'
        admin_user.save()

        parent_user, _ = User.objects.get_or_create(
            username='demo_parent',
            defaults={
                'email': 'parent@smartschool.test',
                'first_name': 'ولي',
                'last_name': 'أمر',
            },
        )
        parent_user.set_password('Demo@12345')
        parent_user.save()

        school, _ = School.objects.get_or_create(
            school_code='DEMO001',
            defaults={
                'name': 'المدرسة الذكية التجريبية',
                'slug': 'demo-school',
                'city': 'الرياض',
                'country': 'السعودية',
                'phone': '0110000000',
                'email': 'info@demo-school.test',
                'academic_year': '2025-2026',
                'address': 'حي الجامعة',
            },
        )
        school.name = 'المدرسة الذكية التجريبية'
        school.city = 'الرياض'
        school.country = 'السعودية'
        school.phone = '0110000000'
        school.email = 'info@demo-school.test'
        school.academic_year = '2025-2026'
        school.address = 'حي الجامعة'
        school.is_active = True
        school.save()

        SchoolMembership.objects.update_or_create(
            user=admin_user,
            school=school,
            defaults={'role': Role.SCHOOL_OWNER, 'is_active': True},
        )
        SchoolMembership.objects.update_or_create(
            user=parent_user,
            school=school,
            defaults={'role': Role.PARENT, 'is_active': True},
        )
        assign_trial_subscription(school, plan_code='professional', days=365)

        # --- Grades 1–6 / classrooms ---
        grades = []
        for order, name in enumerate(GRADE_NAMES, start=1):
            g, _ = GradeLevel.objects.update_or_create(
                school=school, name=name, defaults={'order': order}
            )
            grades.append(g)

        classrooms = []
        for g in grades:
            for section in ['أ', 'ب']:
                c, _ = Classroom.objects.update_or_create(
                    school=school,
                    name=f'{g.name} - {section}',
                    defaults={'grade_level': g, 'section': section, 'capacity': 30},
                )
                classrooms.append(c)

        # --- Subjects ---
        subjects_by_code = {}
        for code, name, _lessons, _max_day in SUBJECT_DEFS:
            s, _ = Subject.objects.update_or_create(
                school=school,
                code=code,
                defaults={'name': name, 'description': f'مادة {name} للمرحلة الابتدائية'},
            )
            subjects_by_code[code] = s
        subjects = [subjects_by_code[c] for c, *_ in SUBJECT_DEFS]

        # --- Teachers (+ logins) ---
        teachers_by_code: dict[str, list[Teacher]] = {c: [] for c, *_ in SUBJECT_DEFS}
        teachers = []
        demo_teacher = None
        for idx, (fn, ln, spec, subj_code, username) in enumerate(TEACHER_DEFS, start=1):
            linked_user = None
            if username:
                linked_user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f'{username}@smartschool.test',
                        'first_name': fn,
                        'last_name': ln,
                    },
                )
                linked_user.set_password('Demo@12345')
                linked_user.first_name = fn
                linked_user.last_name = ln
                linked_user.email = f'{username}@smartschool.test'
                linked_user.save()
                SchoolMembership.objects.update_or_create(
                    user=linked_user,
                    school=school,
                    defaults={'role': Role.TEACHER, 'is_active': True},
                )
            t, _ = Teacher.objects.update_or_create(
                school=school,
                employee_code=f'T-{idx:03d}',
                defaults={
                    'first_name': fn,
                    'last_name': ln,
                    'specialization': spec,
                    'phone': f'055100{idx:04d}',
                    'email': f'teacher{idx}@demo.test',
                    'hire_date': date(2022, 9, 1),
                    'status': 'ACTIVE',
                    'user': linked_user,
                    'notes': f'معلم {spec} — بيانات تجريبية',
                },
            )
            teachers.append(t)
            teachers_by_code[subj_code].append(t)
            if username == 'demo_teacher':
                demo_teacher = t

        # --- Teaching assignments: every subject for every class ---
        assignment_map: dict[tuple[int, int], TeachingAssignment] = {}
        for class_idx, classroom in enumerate(classrooms):
            for code, _name, _lessons, _max_day in SUBJECT_DEFS:
                pool = teachers_by_code[code]
                teacher = pool[class_idx % len(pool)]
                # demo_teacher (Noura) owns Math for Grade 1-A
                if (
                    demo_teacher
                    and classroom == classrooms[0]
                    and code == 'MATH'
                ):
                    teacher = demo_teacher
                ta, _ = TeachingAssignment.objects.get_or_create(
                    school=school,
                    teacher=teacher,
                    subject=subjects_by_code[code],
                    classroom=classroom,
                )
                assignment_map[(classroom.id, subjects_by_code[code].id)] = ta

        # Extra subjects for demo_teacher portal on Grade 1-A
        if demo_teacher and classrooms:
            for code in ('AR', 'EN', 'SCI'):
                TeachingAssignment.objects.get_or_create(
                    school=school,
                    teacher=demo_teacher,
                    subject=subjects_by_code[code],
                    classroom=classrooms[0],
                )
            # Keep primary requirement mapping on subject specialists except MATH
            math = subjects_by_code['MATH']
            ta, _ = TeachingAssignment.objects.get_or_create(
                school=school,
                teacher=demo_teacher,
                subject=math,
                classroom=classrooms[0],
            )
            assignment_map[(classrooms[0].id, math.id)] = ta

        # --- Students (10 per classroom, grades 1–6) ---
        students = []
        student_idx = 0
        for classroom in classrooms:
            grade_order = classroom.grade_level.order
            birth_year = 2019 - (grade_order - 1)
            for i in range(STUDENTS_PER_CLASS):
                student_idx += 1
                is_girl = i % 2 == 1
                names = GIRL_NAMES if is_girl else BOY_NAMES
                fn, father, ln = names[i % len(names)]
                st, _ = Student.objects.update_or_create(
                    school=school,
                    student_code=f'S-{student_idx:04d}',
                    defaults={
                        'first_name': fn,
                        'father_name': father,
                        'last_name': ln,
                        'gender': 'FEMALE' if is_girl else 'MALE',
                        'classroom': classroom,
                        'enrollment_date': date(2025, 9, 1),
                        'phone': f'053{student_idx:07d}',
                        'address': f'حي رقم {(student_idx % 40) + 1}',
                        'status': 'ACTIVE',
                        'notes': f'طالب تجريبي — {classroom.name}',
                        'date_of_birth': date(
                            birth_year,
                            (i % 12) + 1,
                            min(28, i + 1),
                        ),
                    },
                )
                students.append(st)

        # demo_parent → first two students in Grade 1-A
        grade1a_students = [s for s in students if s.classroom_id == classrooms[0].id][:2]
        Parent.objects.filter(school=school, user=parent_user).update(user=None)
        demo_parent_profile, _ = Parent.objects.update_or_create(
            school=school,
            phone='0541999999',
            defaults={
                'name': 'ولي أمر تجريبي',
                'email': 'parent@smartschool.test',
                'relationship': Relationship.FATHER,
                'address': 'حي الجامعة',
                'user': parent_user,
            },
        )
        for student in grade1a_students:
            StudentParent.objects.update_or_create(
                school=school,
                student=student,
                parent=demo_parent_profile,
                defaults={'relationship': Relationship.FATHER, 'is_primary': True},
            )

        for idx, student in enumerate(students, start=1):
            father, _ = Parent.objects.update_or_create(
                school=school,
                phone=f'0541{idx:06d}',
                defaults={
                    'name': f'والد {student.first_name}',
                    'email': f'father{idx}@demo.test',
                    'relationship': Relationship.FATHER,
                    'address': student.address,
                    'user': None,
                },
            )
            mother, _ = Parent.objects.update_or_create(
                school=school,
                phone=f'0542{idx:06d}',
                defaults={
                    'name': f'والدة {student.first_name}',
                    'email': f'mother{idx}@demo.test',
                    'relationship': Relationship.MOTHER,
                    'address': student.address,
                    'user': None,
                },
            )
            StudentParent.objects.update_or_create(
                school=school,
                student=student,
                parent=father,
                defaults={'relationship': Relationship.FATHER, 'is_primary': True},
            )
            StudentParent.objects.update_or_create(
                school=school,
                student=student,
                parent=mother,
                defaults={'relationship': Relationship.MOTHER, 'is_primary': False},
            )

        # --- Transport ---
        drivers = []
        for idx, name in enumerate(['سائق أحمد', 'سائق محمد', 'سائق سعيد', 'سائق فهد'], start=1):
            d, _ = BusDriver.objects.update_or_create(
                school=school,
                phone=f'05600000{idx:02d}',
                defaults={
                    'name': name,
                    'license_number': f'LIC-{100 + idx}',
                    'is_active': True,
                    'notes': 'سائق تجريبي',
                },
            )
            drivers.append(d)

        buses = []
        for idx, (num, vtype, cap) in enumerate(
            [('#01', 'BUS', 40), ('#03', 'BUS', 30), ('Van #05', 'VAN', 12), ('Car #08', 'CAR', 4)],
            start=1,
        ):
            b, _ = Bus.objects.update_or_create(
                school=school,
                bus_number=num,
                defaults={
                    'vehicle_number': f'ABC-{1000 + idx}',
                    'vehicle_type': vtype,
                    'capacity': cap,
                    'driver': drivers[(idx - 1) % len(drivers)],
                    'phone': drivers[(idx - 1) % len(drivers)].phone,
                    'is_active': True,
                    'notes': 'مركبة تجريبية',
                },
            )
            buses.append(b)

        routes = []
        route_defs = [
            ('حي الجامعة → المدرسة', 'حي الجامعة', 'المدرسة', 'محطة 1، محطة 2، محطة 3'),
            ('النخيل → المدرسة', 'حي النخيل', 'المدرسة', 'بوابة النخيل، السوق، المدرسة'),
            ('الملز → المدرسة', 'حي الملز', 'المدرسة', 'الملز، العليا، المدرسة'),
            ('الروضة → المدرسة', 'حي الروضة', 'المدرسة', 'الروضة، التحلية، المدرسة'),
        ]
        for idx, (name, start, end, stops) in enumerate(route_defs):
            r, _ = BusRoute.objects.update_or_create(
                school=school,
                name=name,
                defaults={
                    'start_location': start,
                    'end_location': end,
                    'stops': stops,
                    'bus': buses[idx % len(buses)],
                    'driver': drivers[idx % len(drivers)],
                    'is_active': True,
                    'description': 'مسار تجريبي',
                },
            )
            routes.append(r)

        for idx, student in enumerate(students):
            if idx >= 36:
                break
            StudentTransport.objects.update_or_create(
                school=school,
                student=student,
                defaults={
                    'bus': buses[idx % len(buses)],
                    'route': routes[idx % len(routes)],
                    'pickup_location': 'قرب المنزل',
                    'dropoff_location': 'باب المدرسة',
                    'monthly_fee': Decimal('25.00') + Decimal(idx % 10),
                    'transport_start_date': date(2025, 9, 1),
                    'status': 'ACTIVE' if idx % 15 else 'SUSPENDED',
                    'notes': 'نقل تجريبي',
                },
            )

        # --- Attendance (last 5 school days sample for all students) ---
        for day_offset in range(0, 5):
            day = today - timedelta(days=day_offset)
            for student in students:
                status = 'PRESENT'
                code_num = int(student.student_code.split('-')[-1])
                if code_num % 17 == 0 and day_offset == 0:
                    status = 'ABSENT'
                elif code_num % 13 == 0 and day_offset in {0, 1}:
                    status = 'LATE'
                elif code_num % 19 == 0 and day_offset == 2:
                    status = 'EXCUSED'
                Attendance.objects.update_or_create(
                    school=school,
                    student=student,
                    date=day,
                    defaults={'status': status, 'recorded_by': admin_user, 'notes': ''},
                )

        # --- Grades / assessments ---
        term1, _ = AcademicTerm.objects.update_or_create(
            school=school,
            name='الفصل الأول',
            academic_year='2025-2026',
            defaults={
                'is_current': True,
                'start_date': date(2025, 9, 1),
                'end_date': date(2026, 1, 15),
            },
        )
        AcademicTerm.objects.update_or_create(
            school=school,
            name='الفصل الثاني',
            academic_year='2025-2026',
            defaults={
                'is_current': False,
                'start_date': date(2026, 2, 1),
                'end_date': date(2026, 6, 15),
            },
        )

        core_codes = ['MATH', 'AR', 'EN', 'SCI']
        assessments = []
        for code in core_codes:
            subject = subjects_by_code[code]
            for classroom in classrooms:
                for atype, aname, max_score, days_ago in [
                    (AssessmentType.QUIZ, f'مذاكرة {subject.name}', Decimal('20'), 10),
                    (AssessmentType.MIDTERM, f'امتحان نصفي {subject.name}', Decimal('30'), 5),
                    (AssessmentType.FINAL, f'امتحان نهائي {subject.name}', Decimal('50'), 1),
                ]:
                    a, _ = Assessment.objects.update_or_create(
                        school=school,
                        name=aname,
                        subject=subject,
                        classroom=classroom,
                        term=term1,
                        defaults={
                            'assessment_type': atype,
                            'max_score': max_score,
                            'date': today - timedelta(days=days_ago),
                        },
                    )
                    assessments.append(a)

        for assessment in assessments:
            class_students = [s for s in students if s.classroom_id == assessment.classroom_id]
            for i, student in enumerate(class_students):
                max_score = float(assessment.max_score)
                base = max_score * 0.7
                Grade.objects.update_or_create(
                    school=school,
                    student=student,
                    assessment=assessment,
                    defaults={
                        'score': Decimal(str(round(base + (i * 1.5) % (max_score * 0.25), 2))),
                        'notes': '',
                    },
                )

        # --- Finance ---
        for student in students:
            fee = Fee.objects.filter(
                school=school, student=student, title='رسوم سنوية'
            ).order_by('id').first()
            if fee is None:
                fee = Fee.objects.create(
                    school=school,
                    student=student,
                    title='رسوم سنوية',
                    academic_year='2025-2026',
                    amount=Decimal('5000'),
                    due_date=date(2025, 10, 1),
                    notes='رسوم دراسية',
                )
            else:
                fee.academic_year = '2025-2026'
                fee.amount = Decimal('5000')
                fee.due_date = date(2025, 10, 1)
                fee.notes = 'رسوم دراسية'
                fee.save()
            code_num = int(student.student_code.split('-')[-1])
            paid = Decimal('2000') if code_num <= 40 else Decimal('0')
            if paid:
                Payment.objects.update_or_create(
                    school=school,
                    fee=fee,
                    student=student,
                    reference=f'PAY-{student.student_code}',
                    defaults={
                        'amount': paid,
                        'payment_date': today - timedelta(days=2),
                        'method': 'cash',
                        'notes': 'دفعة جزئية',
                    },
                )
            Invoice.objects.update_or_create(
                school=school,
                invoice_number=f'INV-{student.student_code}',
                defaults={
                    'student': student,
                    'fee': fee,
                    'amount': fee.amount,
                    'issued_at': date(2025, 9, 5),
                    'status': 'ISSUED',
                },
            )
            StudentAccount.objects.update_or_create(
                school=school,
                student=student,
                defaults={'balance': fee.amount - paid},
            )

        for title, category, amount in [
            ('صيانة حافلات', 'transport', Decimal('800')),
            ('مستلزمات مكتبية', 'supplies', Decimal('350')),
            ('كهرباء', 'utilities', Decimal('1200')),
            ('أنشطة طلابية', 'activities', Decimal('500')),
        ]:
            Expense.objects.update_or_create(
                school=school,
                title=title,
                expense_date=today,
                defaults={'category': category, 'amount': amount, 'notes': 'مصروف تجريبي'},
            )

        # --- Weekly timetable (grades 1–6) ---
        timetable, _ = Timetable.objects.update_or_create(
            school=school,
            name='الجدول الرئيسي',
            academic_year='2025-2026',
            defaults={
                'working_days': [0, 1, 2, 3, 4],
                'period_duration_minutes': 45,
                'notes': 'جدول تجريبي للصفوف 1–6',
                'status': TimetableStatus.DRAFT,
                'published_at': None,
            },
        )
        # Ensure editable draft for regeneration
        Timetable.objects.filter(pk=timetable.pk).update(
            status=TimetableStatus.DRAFT, published_at=None
        )
        timetable.refresh_from_db()
        timetable.entries.all().delete()
        timetable.requirements.all().delete()
        timetable.periods.all().delete()

        period_plan = [
            (1, 'الحصة 1', time(8, 0), time(8, 45), False),
            (2, 'الحصة 2', time(8, 45), time(9, 30), False),
            (3, 'الحصة 3', time(9, 30), time(10, 15), False),
            (4, 'استراحة', time(10, 15), time(10, 30), True),
            (5, 'الحصة 4', time(10, 30), time(11, 15), False),
            (6, 'الحصة 5', time(11, 15), time(12, 0), False),
            (7, 'الحصة 6', time(12, 0), time(12, 45), False),
        ]
        for num, label, start, end, is_break in period_plan:
            TimetablePeriod.objects.create(
                timetable=timetable,
                period_number=num,
                label=label,
                start_time=start,
                end_time=end,
                is_break=is_break,
            )

        for classroom in classrooms:
            for code, _name, lessons, max_day in SUBJECT_DEFS:
                subject = subjects_by_code[code]
                ta = assignment_map.get((classroom.id, subject.id))
                if not ta:
                    continue
                WeeklySubjectRequirement.objects.create(
                    school=school,
                    timetable=timetable,
                    classroom=classroom,
                    subject=subject,
                    teaching_assignment=ta,
                    lessons_per_week=lessons,
                    max_lessons_per_day=max_day,
                    preferred_lessons_per_day=1,
                )

        gen = generate_timetable(timetable, replace_existing=True)
        applied = 0
        if gen.get('proposed'):
            applied = apply_generated_entries(
                timetable, gen['proposed'], replace_existing=True
            )
        # If generator left gaps, leave draft validation warnings; still publish if no hard conflicts
        try:
            publish_timetable(timetable)
            tt_status = 'PUBLISHED'
        except ValueError:
            # Keep draft if conflicts remain
            tt_status = 'DRAFT'

        for ntype, title, body, audience in [
            ('SYSTEM', 'مرحباً بك في النسخة التجريبية', 'تم تجهيز بيانات تجريبية كاملة للصفوف 1–6.', NotificationAudience.ALL),
            ('ATTENDANCE', 'تنبيه غياب', 'يوجد طلاب غائبون اليوم.', NotificationAudience.MANAGERS),
            ('TRANSPORT', 'سعة الحافلة', 'الحافلة #03 قريبة من الامتلاء.', NotificationAudience.MANAGERS),
            ('PAYMENT', 'مدفوعات متبقية', 'بعض الرسوم السنوية ما زالت غير مكتملة.', NotificationAudience.PARENTS),
            ('ANNOUNCEMENT', 'إعلان عام', 'بداية اختبارات منتصف الفصل الأسبوع القادم.', NotificationAudience.ALL),
            ('ACADEMIC', 'نتائج الاختبارات', 'تم رصد درجات اختبار منتصف الفصل.', NotificationAudience.PARENTS),
            ('ACADEMIC', 'تذكير رصد الدرجات', 'يرجى إكمال إدخال درجات المذاكرة لهذا الأسبوع.', NotificationAudience.TEACHERS),
            ('ATTENDANCE', 'حضور اليوم', 'تم تسجيل حضور فصول المرحلة الابتدائية.', NotificationAudience.TEACHERS),
            ('ACADEMIC', 'الجدول الدراسي', 'تم نشر الجدول الرئيسي للعام 2025-2026.', NotificationAudience.TEACHERS),
        ]:
            Notification.objects.update_or_create(
                school=school,
                title=title,
                defaults={
                    'type': ntype,
                    'body': body,
                    'user': None,
                    'audience': audience,
                    'is_read': False,
                    'metadata': {'source': 'seed_demo'},
                },
            )

        self.stdout.write(self.style.SUCCESS('Demo data ready (grades 1–6).'))
        self.stdout.write('Admin login: demo_admin / Demo@12345')
        self.stdout.write('Teacher login: demo_teacher / Demo@12345')
        self.stdout.write('Parent login: demo_parent / Demo@12345')
        self.stdout.write('Other teachers: teacher_sci / teacher_ar / teacher_en / ... / Demo@12345')
        self.stdout.write(f'School code: {school.school_code}')
        self.stdout.write(f'School id: {school.id}')
        self.stdout.write(
            f'Counts => grades={len(grades)} classrooms={len(classrooms)} '
            f'students={Student.objects.filter(school=school, classroom__in=classrooms).count()} '
            f'teachers={Teacher.objects.filter(school=school).count()} '
            f'assignments={TeachingAssignment.objects.filter(school=school).count()} '
            f'timetable_entries={TimetableEntry.objects.filter(timetable=timetable).count()} '
            f'timetable_status={tt_status} generated={gen.get("success")} applied={applied}'
        )
