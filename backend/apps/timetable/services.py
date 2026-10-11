"""Timetable validation, conflict detection, and rule-based generation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction

from apps.academics.models import TeachingAssignment
from apps.timetable.models import (
    TeacherAvailability,
    Timetable,
    TimetableEntry,
    TimetablePeriod,
    TimetableStatus,
    WeeklySubjectRequirement,
)


@dataclass
class Issue:
    code: str
    severity: str  # error | warning
    message: str
    message_ar: str
    meta: dict = field(default_factory=dict)


def _teacher_id_from_assignment(assignment: TeachingAssignment) -> int:
    return assignment.teacher_id


def is_teacher_available(school, teacher_id: int, day: int, period_number: int) -> bool:
    rules = list(
        TeacherAvailability.objects.filter(school=school, teacher_id=teacher_id, day=day)
    )
    if not rules:
        return True
    day_rule = next((r for r in rules if r.period_number is None), None)
    if day_rule is not None and not day_rule.is_available:
        return False
    period_rule = next((r for r in rules if r.period_number == period_number), None)
    if period_rule is not None:
        return period_rule.is_available
    # If only positive availability rows exist for other periods, remain available by default.
    return True


def validate_entry_payload(
    *,
    school,
    timetable: Timetable,
    day: int,
    period: TimetablePeriod,
    classroom_id: int,
    subject_id: int,
    teaching_assignment: TeachingAssignment,
    exclude_entry_id: int | None = None,
) -> list[Issue]:
    issues: list[Issue] = []

    if period.timetable_id != timetable.id:
        issues.append(
            Issue(
                'invalid_period',
                'error',
                'Period does not belong to this timetable.',
                'الحصة لا تنتمي إلى هذا الجدول.',
            )
        )
    if period.is_break:
        issues.append(
            Issue(
                'break_slot',
                'error',
                'Cannot place a lesson in a break period.',
                'لا يمكن وضع حصة في فترة استراحة.',
            )
        )
    if day not in timetable.get_working_days():
        issues.append(
            Issue(
                'non_working_day',
                'error',
                'Selected day is not a working day.',
                'اليوم المحدد ليس ضمن أيام العمل.',
            )
        )

    ta = teaching_assignment
    if ta.school_id != school.id:
        issues.append(
            Issue(
                'cross_tenant_assignment',
                'error',
                'Teaching assignment belongs to another school.',
                'تكليف التدريس لا ينتمي إلى هذه المدرسة.',
            )
        )
    if ta.classroom_id != classroom_id or ta.subject_id != subject_id:
        issues.append(
            Issue(
                'invalid_assignment',
                'error',
                'Teacher is not assigned to this subject/class.',
                'المعلم غير مكلّف بهذه المادة/الفصل.',
            )
        )

    entries = TimetableEntry.objects.filter(
        timetable=timetable, day=day, period=period
    ).select_related('teaching_assignment', 'classroom', 'subject')
    if exclude_entry_id:
        entries = entries.exclude(pk=exclude_entry_id)

    for e in entries:
        if e.classroom_id == classroom_id:
            issues.append(
                Issue(
                    'class_conflict',
                    'error',
                    f'Classroom already has a lesson in this period.',
                    'الفصل لديه حصة أخرى في نفس الوقت.',
                    {'entry_id': e.id},
                )
            )
        if e.teaching_assignment.teacher_id == ta.teacher_id:
            issues.append(
                Issue(
                    'teacher_conflict',
                    'error',
                    'Teacher already teaches another class in this period.',
                    'المعلم لديه حصة أخرى في نفس الوقت.',
                    {'entry_id': e.id, 'classroom': e.classroom.name},
                )
            )

    if not is_teacher_available(school, ta.teacher_id, day, period.period_number):
        issues.append(
            Issue(
                'teacher_unavailable',
                'error',
                'Teacher is unavailable for this day/period.',
                'المعلم غير متاح في هذا اليوم/الحصة.',
            )
        )

    return issues


def validate_timetable(timetable: Timetable) -> dict:
    """Full validation: conflicts + weekly requirements coverage."""
    issues: list[Issue] = []
    entries = list(
        timetable.entries.select_related(
            'period', 'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
    )
    requirements = list(
        timetable.requirements.select_related('classroom', 'subject', 'teaching_assignment')
    )

    # Slot conflicts in memory
    by_class_slot: dict[tuple, list] = defaultdict(list)
    by_teacher_slot: dict[tuple, list] = defaultdict(list)
    for e in entries:
        if e.period.is_break:
            issues.append(
                Issue(
                    'break_slot',
                    'error',
                    'Lesson placed in break.',
                    f'حصة داخل استراحة: {e.classroom.name}.',
                    {'entry_id': e.id},
                )
            )
            continue
        ck = (e.day, e.period_id, e.classroom_id)
        tk = (e.day, e.period_id, e.teaching_assignment.teacher_id)
        by_class_slot[ck].append(e)
        by_teacher_slot[tk].append(e)
        if e.teaching_assignment.classroom_id != e.classroom_id or e.teaching_assignment.subject_id != e.subject_id:
            issues.append(
                Issue(
                    'invalid_assignment',
                    'error',
                    'Invalid teaching assignment on entry.',
                    f'تكليف غير صالح: {e.classroom.name} / {e.subject.name}.',
                    {'entry_id': e.id},
                )
            )
        if not is_teacher_available(
            timetable.school, e.teaching_assignment.teacher_id, e.day, e.period.period_number
        ):
            issues.append(
                Issue(
                    'teacher_unavailable',
                    'error',
                    'Teacher unavailable.',
                    f'المعلم غير متاح: {e.teaching_assignment.teacher}.',
                    {'entry_id': e.id},
                )
            )

    for key, group in by_class_slot.items():
        if len(group) > 1:
            issues.append(
                Issue(
                    'class_conflict',
                    'error',
                    'Class conflict.',
                    f'تعارض فصل في يوم {key[0]} حصة {group[0].period.period_number}.',
                )
            )
    for key, group in by_teacher_slot.items():
        if len(group) > 1:
            issues.append(
                Issue(
                    'teacher_conflict',
                    'error',
                    'Teacher conflict.',
                    f'تعارض معلم في يوم {key[0]} حصة {group[0].period.period_number}.',
                )
            )

    # Weekly requirements
    scheduled: dict[tuple[int, int], list] = defaultdict(list)
    for e in entries:
        scheduled[(e.classroom_id, e.subject_id)].append(e)

    for req in requirements:
        key = (req.classroom_id, req.subject_id)
        placed = scheduled.get(key, [])
        count = len(placed)
        if count < req.lessons_per_week:
            issues.append(
                Issue(
                    'requirement_incomplete',
                    'warning',
                    f'{req.lessons_per_week - count} lesson(s) still missing.',
                    f'متبقّي {req.lessons_per_week - count} حصة لـ {req.subject.name} — {req.classroom.name}.',
                    {
                        'classroom_id': req.classroom_id,
                        'subject_id': req.subject_id,
                        'required': req.lessons_per_week,
                        'scheduled': count,
                    },
                )
            )
        elif count > req.lessons_per_week:
            issues.append(
                Issue(
                    'requirement_overflow',
                    'warning',
                    f'Weekly requirement exceeded by {count - req.lessons_per_week}.',
                    f'تجاوز المطلوب بمقدار {count - req.lessons_per_week} لـ {req.subject.name} — {req.classroom.name}.',
                    {
                        'classroom_id': req.classroom_id,
                        'subject_id': req.subject_id,
                        'required': req.lessons_per_week,
                        'scheduled': count,
                    },
                )
            )

        if req.max_lessons_per_day:
            per_day: dict[int, int] = defaultdict(int)
            for e in placed:
                per_day[e.day] += 1
            for day, n in per_day.items():
                if n > req.max_lessons_per_day:
                    issues.append(
                        Issue(
                            'max_per_day',
                            'warning',
                            'Max lessons per day exceeded.',
                            f'{req.subject.name} في {req.classroom.name}: {n} حصص في يوم واحد (الحد {req.max_lessons_per_day}).',
                            {'day': day},
                        )
                    )

    errors = [i for i in issues if i.severity == 'error']
    warnings = [i for i in issues if i.severity == 'warning']
    return {
        'ok': len(errors) == 0 and len(warnings) == 0,
        'ready_to_publish': len(errors) == 0 and not any(
            i.code == 'requirement_incomplete' for i in warnings
        ),
        'errors': [i.__dict__ for i in errors],
        'warnings': [i.__dict__ for i in warnings],
        'stats': {
            'entries': len(entries),
            'requirements': len(requirements),
            'required_lessons': sum(r.lessons_per_week for r in requirements),
            'scheduled_lessons': len(entries),
        },
    }


def generate_timetable(timetable: Timetable, *, replace_existing: bool = False) -> dict:
    """
    In-memory greedy generator.
    Does not write until caller confirms (when replace_existing and save).
    Returns proposed entries + validation summary.
    """
    periods = list(
        timetable.periods.filter(is_break=False).order_by('period_number')
    )
    days = timetable.get_working_days()
    requirements = list(
        timetable.requirements.select_related(
            'classroom', 'subject', 'teaching_assignment', 'teaching_assignment__teacher'
        )
    )

    if not periods:
        return {
            'success': False,
            'message_ar': 'لا توجد حصص معرّفة (غير الاستراحات).',
            'proposed': [],
            'problems': [{'message_ar': 'أضف حصصاً للجدول أولاً.'}],
        }
    if not days:
        return {
            'success': False,
            'message_ar': 'أيام العمل غير محددة.',
            'proposed': [],
            'problems': [],
        }
    if not requirements:
        return {
            'success': False,
            'message_ar': 'لا توجد متطلبات أسبوعية.',
            'proposed': [],
            'problems': [],
        }

    # Occupancy maps
    class_busy: set[tuple[int, int, int]] = set()  # day, period_id, classroom_id
    teacher_busy: set[tuple[int, int, int]] = set()  # day, period_id, teacher_id
    subject_day_count: dict[tuple[int, int, int], int] = defaultdict(int)  # classroom, subject, day

    if not replace_existing:
        for e in timetable.entries.select_related('teaching_assignment', 'period'):
            if e.period.is_break:
                continue
            class_busy.add((e.day, e.period_id, e.classroom_id))
            teacher_busy.add((e.day, e.period_id, e.teaching_assignment.teacher_id))
            subject_day_count[(e.classroom_id, e.subject_id, e.day)] += 1

    # Sort requirements: larger load first
    reqs = sorted(requirements, key=lambda r: (-r.lessons_per_week, r.classroom_id, r.subject_id))
    proposed: list[dict] = []
    problems: list[dict] = []

    # Existing scheduled counts when not replacing
    existing_counts: dict[tuple[int, int], int] = defaultdict(int)
    if not replace_existing:
        for e in timetable.entries.all():
            existing_counts[(e.classroom_id, e.subject_id)] += 1

    for req in reqs:
        need = req.lessons_per_week - (0 if replace_existing else existing_counts[(req.classroom_id, req.subject_id)])
        if need <= 0:
            continue
        teacher_id = req.teaching_assignment.teacher_id
        placed = 0
        # Prefer spreading across days
        day_order = list(days)
        attempts = 0
        while placed < need and attempts < need * len(days) * len(periods) + 10:
            attempts += 1
            progress = False
            for day in day_order:
                if placed >= need:
                    break
                max_day = req.max_lessons_per_day or 99
                if subject_day_count[(req.classroom_id, req.subject_id, day)] >= max_day:
                    continue
                for period in periods:
                    if placed >= need:
                        break
                    if not is_teacher_available(
                        timetable.school, teacher_id, day, period.period_number
                    ):
                        continue
                    ck = (day, period.id, req.classroom_id)
                    tk = (day, period.id, teacher_id)
                    if ck in class_busy or tk in teacher_busy:
                        continue
                    class_busy.add(ck)
                    teacher_busy.add(tk)
                    subject_day_count[(req.classroom_id, req.subject_id, day)] += 1
                    proposed.append(
                        {
                            'day': day,
                            'period_id': period.id,
                            'period_number': period.period_number,
                            'classroom_id': req.classroom_id,
                            'classroom_name': req.classroom.name,
                            'subject_id': req.subject_id,
                            'subject_name': req.subject.name,
                            'teaching_assignment_id': req.teaching_assignment_id,
                            'teacher_id': teacher_id,
                            'teacher_name': str(req.teaching_assignment.teacher),
                        }
                    )
                    placed += 1
                    progress = True
            if not progress:
                break
            # rotate days to spread
            day_order = day_order[1:] + day_order[:1]

        if placed < need:
            problems.append(
                {
                    'classroom': req.classroom.name,
                    'subject': req.subject.name,
                    'required': req.lessons_per_week,
                    'scheduled_now': (0 if replace_existing else existing_counts[(req.classroom_id, req.subject_id)])
                    + placed,
                    'message_ar': (
                        f'{req.classroom.name} / {req.subject.name}: المطلوب {req.lessons_per_week}، '
                        f'تم اقتراح {placed} فقط (قد يكون بسبب تعارضات أو عدم توفر المعلم).'
                    ),
                }
            )

    success = len(problems) == 0
    return {
        'success': success,
        'message_ar': (
            'تم توليد اقتراح جدول بنجاح.'
            if success
            else 'تعذر توليد جدول كامل. راجع المشكلات أدناه.'
        ),
        'proposed': proposed,
        'problems': problems,
        'stats': {
            'proposed_lessons': len(proposed),
            'classes': len({r.classroom_id for r in requirements}),
            'requirements': len(requirements),
        },
        'replace_existing': replace_existing,
    }


@transaction.atomic
def apply_generated_entries(timetable: Timetable, proposed: list[dict], *, replace_existing: bool) -> int:
    if timetable.status == TimetableStatus.PUBLISHED:
        raise ValueError('Cannot overwrite a published timetable. Archive or create a draft copy.')
    if replace_existing:
        timetable.entries.all().delete()
    created = 0
    for item in proposed:
        period = TimetablePeriod.objects.get(id=item['period_id'], timetable=timetable)
        ta = TeachingAssignment.objects.get(id=item['teaching_assignment_id'])
        issues = validate_entry_payload(
            school=timetable.school,
            timetable=timetable,
            day=item['day'],
            period=period,
            classroom_id=item['classroom_id'],
            subject_id=item['subject_id'],
            teaching_assignment=ta,
        )
        if any(i.severity == 'error' for i in issues):
            continue
        TimetableEntry.objects.create(
            school=timetable.school,
            timetable=timetable,
            day=item['day'],
            period=period,
            classroom_id=item['classroom_id'],
            subject_id=item['subject_id'],
            teaching_assignment=ta,
        )
        created += 1
    return created


@transaction.atomic
def publish_timetable(timetable: Timetable) -> Timetable:
    from django.utils import timezone

    report = validate_timetable(timetable)
    if report['errors']:
        raise ValueError('Cannot publish timetable with conflicts.')
    # Archive other published for same school+year optionally
    Timetable.objects.filter(
        school=timetable.school,
        academic_year=timetable.academic_year,
        status=TimetableStatus.PUBLISHED,
    ).exclude(pk=timetable.pk).update(status=TimetableStatus.ARCHIVED)
    timetable.status = TimetableStatus.PUBLISHED
    timetable.published_at = timezone.now()
    timetable.save(update_fields=['status', 'published_at', 'updated_at'])
    return timetable


def notify_timetable_published(timetable: Timetable) -> int:
    """Notify teachers who have lessons in this timetable."""
    from apps.notifications.models import NotificationType
    from apps.notifications.services import notify_user

    teacher_ids = set(
        timetable.entries.values_list('teaching_assignment__teacher__user_id', flat=True)
    )
    count = 0
    for user_id in teacher_ids:
        if not user_id:
            continue
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(id=user_id).first()
        if not user:
            continue
        notify_user(
            school=timetable.school,
            user=user,
            title='تم تحديث الجدول الدراسي',
            body=f'تم نشر الجدول «{timetable.name}» للعام {timetable.academic_year}.',
            type=NotificationType.ACADEMIC,
            metadata={'event': 'TimetablePublished', 'timetable_id': timetable.id},
        )
        count += 1
    return count
