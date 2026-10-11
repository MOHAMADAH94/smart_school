"""Rule-based Smart School Center insight engine (calculated, not persisted)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.finance.models import Fee, Payment
from apps.grades.models import Grade
from apps.schools.roles import Permission, Role, role_has_permission
from apps.students.models import Student
from apps.subscriptions.services import school_has_feature
from apps.transport.models import Bus, StudentTransport


def _insight(
    *,
    code: str,
    severity: str,
    title: str,
    message: str,
    message_ar: str,
    metric=None,
    action_type: str | None = None,
    action_label: str | None = None,
    action_path: str | None = None,
) -> dict:
    return {
        'code': code,
        'severity': severity,
        'title': title,
        'message': message,
        'message_ar': message_ar,
        'metric': metric,
        'action_type': action_type,
        'action_label': action_label,
        'action_path': action_path,
    }


def _month_bounds(today):
    month_start = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    return month_start, next_month, prev_month_start, prev_month_end


def build_attendance_insights(school, today) -> tuple[list[dict], dict]:
    insights: list[dict] = []
    month_start, _, _, _ = _month_bounds(today)
    week_ago = today - timedelta(days=7)

    today_qs = Attendance.objects.filter(school=school, date=today)
    today_total = today_qs.count()
    today_absent = today_qs.filter(status='ABSENT').count()
    today_present = today_qs.exclude(status='ABSENT').count()
    today_rate = round((today_present / today_total) * 100, 1) if today_total else None

    week_qs = Attendance.objects.filter(school=school, date__gte=week_ago, date__lte=today)
    week_total = week_qs.count()
    week_present = week_qs.exclude(status='ABSENT').count()
    week_rate = round((week_present / week_total) * 100, 1) if week_total else None

    month_qs = Attendance.objects.filter(school=school, date__gte=month_start, date__lte=today)
    month_total = month_qs.count()
    month_absent = month_qs.filter(status='ABSENT').count()
    month_present = month_qs.exclude(status='ABSENT').count()
    month_rate = round((month_present / month_total) * 100, 1) if month_total else None

    metrics = {
        'today_attendance_rate': today_rate,
        'today_absence_count': today_absent,
        'weekly_attendance_rate': week_rate,
        'monthly_attendance_rate': month_rate,
    }

    if today_absent:
        insights.append(
            _insight(
                code='absent_today',
                severity='medium' if today_absent < 10 else 'high',
                title='غياب اليوم',
                message=f'{today_absent} students are absent today.',
                message_ar=f'{today_absent} طالب غائب اليوم.',
                metric=today_absent,
                action_type='view_attendance',
                action_label='عرض الحضور',
                action_path='/attendance',
            )
        )

    # Repeated absences this month (3+)
    repeated = (
        Attendance.objects.filter(school=school, date__gte=month_start, status='ABSENT')
        .values('student_id', 'student__first_name', 'student__last_name')
        .annotate(c=Count('id'))
        .filter(c__gte=3)
    )
    repeated_count = repeated.count()
    metrics['repeated_absence_students'] = repeated_count
    if repeated_count:
        insights.append(
            _insight(
                code='repeated_absences',
                severity='high',
                title='غياب متكرر',
                message=f'{repeated_count} students have been absent 3 or more times this month.',
                message_ar=f'{repeated_count} طالب تغيبوا 3 مرات أو أكثر هذا الشهر.',
                metric=repeated_count,
                action_type='view_attendance',
                action_label='عرض الطلاب',
                action_path='/attendance',
            )
        )

    # Highest absence class vs school average
    class_stats = list(
        Attendance.objects.filter(
            school=school,
            date__gte=month_start,
            student__classroom__isnull=False,
        )
        .values('student__classroom_id', 'student__classroom__name')
        .annotate(
            total=Count('id'),
            absences=Count('id', filter=Q(status='ABSENT')),
        )
    )
    school_avg = (month_absent / month_total * 100) if month_total else 0
    worst = None
    worst_rate = -1.0
    for row in class_stats:
        if not row['total']:
            continue
        rate = (row['absences'] / row['total']) * 100
        if rate > worst_rate:
            worst_rate = rate
            worst = row
    if worst and worst_rate >= 10:
        delta = round(worst_rate - school_avg, 1)
        name = worst['student__classroom__name']
        insights.append(
            _insight(
                code='highest_absence_class',
                severity='medium' if delta < 5 else 'high',
                title='أعلى غياب حسب الفصل',
                message=(
                    f'{name} has a {round(worst_rate, 1)}% absence rate this month'
                    + (f', which is {delta}% above the school average.' if delta > 0 else '.')
                ),
                message_ar=(
                    f'الفصل {name} لديه معدل غياب {round(worst_rate, 1)}% هذا الشهر'
                    + (f'، أعلى من متوسط المدرسة بمقدار {delta}%.' if delta > 0 else '.')
                ),
                metric={'class': name, 'rate': round(worst_rate, 1), 'delta': delta},
                action_type='view_attendance',
                action_label='عرض الحضور',
                action_path='/attendance',
            )
        )
    metrics['highest_absence_class'] = (
        {'name': worst['student__classroom__name'], 'rate': round(worst_rate, 1)} if worst else None
    )

    # Week-over-week trend
    prev_week_start = week_ago - timedelta(days=7)
    this_week_abs = Attendance.objects.filter(
        school=school, date__gte=week_ago, date__lte=today, status='ABSENT'
    ).count()
    prev_week_abs = Attendance.objects.filter(
        school=school, date__gte=prev_week_start, date__lt=week_ago, status='ABSENT'
    ).count()
    if prev_week_abs:
        if this_week_abs > prev_week_abs:
            insights.append(
                _insight(
                    code='attendance_down',
                    severity='low',
                    title='اتجاه الحضور',
                    message='Absences increased compared with last week.',
                    message_ar='ازداد الغياب مقارنة بالأسبوع الماضي.',
                    metric={'this_week': this_week_abs, 'last_week': prev_week_abs},
                )
            )
        metrics['absence_trend'] = {
            'this_week': this_week_abs,
            'last_week': prev_week_abs,
            'label': 'compared' if prev_week_abs else 'not_enough_data',
        }
    else:
        metrics['absence_trend'] = {'label': 'not_enough_data'}

    return insights, metrics


def build_academic_insights(school, today) -> tuple[list[dict], dict]:
    insights: list[dict] = []
    metrics: dict = {}

    subject_avgs = list(
        Grade.objects.filter(school=school)
        .values('assessment__subject_id', 'assessment__subject__name')
        .annotate(avg=Avg('score'), n=Count('id'))
        .filter(n__gte=3)
        .order_by('avg')
    )
    if not subject_avgs:
        metrics['note'] = 'not_enough_data'
        return insights, metrics

    lowest = subject_avgs[0]
    highest = subject_avgs[-1]
    metrics['lowest_subject'] = {
        'name': lowest['assessment__subject__name'],
        'avg': round(float(lowest['avg'] or 0), 2),
    }
    metrics['highest_subject'] = {
        'name': highest['assessment__subject__name'],
        'avg': round(float(highest['avg'] or 0), 2),
    }
    metrics['class_average'] = round(
        float(
            Grade.objects.filter(school=school).aggregate(a=Avg('score'))['a'] or 0
        ),
        2,
    )

    # Term comparison when two terms have grades
    term_avgs = list(
        Grade.objects.filter(school=school, assessment__term__isnull=False)
        .values('assessment__term_id', 'assessment__term__name', 'assessment__term__start_date')
        .annotate(avg=Avg('score'), n=Count('id'))
        .filter(n__gte=5)
        .order_by('-assessment__term__start_date')[:2]
    )
    if len(term_avgs) >= 2:
        current, previous = term_avgs[0], term_avgs[1]
        cur_avg = float(current['avg'] or 0)
        prev_avg = float(previous['avg'] or 0)
        if prev_avg:
            delta = round(cur_avg - prev_avg, 1)
            metrics['term_trend'] = {
                'current': round(cur_avg, 2),
                'previous': round(prev_avg, 2),
                'delta': delta,
            }
            if delta <= -5:
                insights.append(
                    _insight(
                        code='term_average_down',
                        severity='medium',
                        title='متوسط الفصل الدراسي',
                        message=(
                            f'Overall average decreased by {abs(delta)}% compared with the previous term.'
                        ),
                        message_ar=(
                            f'انخفض المتوسط العام بمقدار {abs(delta)}% مقارنة بالفصل السابق.'
                        ),
                        metric=metrics['term_trend'],
                        action_type='view_grades',
                        action_label='عرض الدرجات',
                        action_path='/grades',
                    )
                )
        else:
            metrics['term_trend'] = {'label': 'not_enough_data'}
    else:
        metrics['term_trend'] = {'label': 'not_enough_data'}

    # Subject decline vs previous term (same subject)
    if len(term_avgs) >= 2:
        cur_term_id = term_avgs[0]['assessment__term_id']
        prev_term_id = term_avgs[1]['assessment__term_id']
        cur_by_subj = {
            r['assessment__subject_id']: r
            for r in Grade.objects.filter(school=school, assessment__term_id=cur_term_id)
            .values('assessment__subject_id', 'assessment__subject__name')
            .annotate(avg=Avg('score'), n=Count('id'))
            .filter(n__gte=3)
        }
        prev_by_subj = {
            r['assessment__subject_id']: r
            for r in Grade.objects.filter(school=school, assessment__term_id=prev_term_id)
            .values('assessment__subject_id', 'assessment__subject__name')
            .annotate(avg=Avg('score'), n=Count('id'))
            .filter(n__gte=3)
        }
        biggest_drop = None
        for sid, cur in cur_by_subj.items():
            prev = prev_by_subj.get(sid)
            if not prev or not prev['avg']:
                continue
            delta = float(cur['avg']) - float(prev['avg'])
            if biggest_drop is None or delta < biggest_drop[0]:
                biggest_drop = (delta, cur['assessment__subject__name'])
        if biggest_drop and biggest_drop[0] <= -5:
            delta, name = biggest_drop
            insights.append(
                _insight(
                    code='subject_decline',
                    severity='medium',
                    title='انخفاض مادة',
                    message=f'{name} decreased by {abs(round(delta, 1))}% compared with the previous term.',
                    message_ar=f'انخفض متوسط {name} بمقدار {abs(round(delta, 1))}% مقارنة بالفصل السابق.',
                    metric={'subject': name, 'delta': round(delta, 1)},
                    action_type='view_grades',
                    action_label='عرض التقرير الأكاديمي',
                    action_path='/grades',
                )
            )

    return insights, metrics


def build_financial_insights(school, today) -> tuple[list[dict], dict]:
    insights: list[dict] = []
    month_start, _, prev_month_start, prev_month_end = _month_bounds(today)

    total_fees = Fee.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    paid = Payment.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    outstanding = total_fees - paid
    collection_rate = round(float(paid) / float(total_fees) * 100, 1) if total_fees else None

    # Overdue: fees past due_date with remaining balance > 0
    overdue_students = set()
    overdue_amount = Decimal('0')
    for fee in Fee.objects.filter(school=school, due_date__lt=today).prefetch_related('payments'):
        remaining = fee.amount - sum((p.amount for p in fee.payments.all()), Decimal('0'))
        if remaining > 0:
            overdue_students.add(fee.student_id)
            overdue_amount += remaining

    metrics = {
        'total_fees': total_fees,
        'paid': paid,
        'outstanding': outstanding,
        'overdue': overdue_amount,
        'overdue_students': len(overdue_students),
        'collection_rate': collection_rate,
    }

    if overdue_students:
        insights.append(
            _insight(
                code='overdue_fees',
                severity='high',
                title='رسوم متأخرة',
                message=f'{len(overdue_students)} students have overdue balances.',
                message_ar=f'{len(overdue_students)} طالب لديهم أرصدة متأخرة.',
                metric={'students': len(overdue_students), 'amount': str(overdue_amount)},
                action_type='view_payments',
                action_label='عرض المستحقات',
                action_path='/finance',
            )
        )
    elif outstanding > 0:
        insights.append(
            _insight(
                code='outstanding_fees',
                severity='medium',
                title='رسوم مستحقة',
                message=f'Outstanding fees total {outstanding}.',
                message_ar=f'إجمالي الرسوم المستحقة {outstanding}.',
                metric=str(outstanding),
                action_type='view_payments',
                action_label='عرض المدفوعات',
                action_path='/finance',
            )
        )

    paid_this = Payment.objects.filter(
        school=school, payment_date__gte=month_start, payment_date__lte=today
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    paid_prev = Payment.objects.filter(
        school=school, payment_date__gte=prev_month_start, payment_date__lte=prev_month_end
    ).aggregate(s=Sum('amount'))['s'] or Decimal('0')
    if paid_prev:
        # Compare outstanding change using fee/payment totals is heavy; use collection month trend
        delta_pct = round((float(paid_this) - float(paid_prev)) / float(paid_prev) * 100, 1)
        metrics['collection_trend'] = {
            'this_month': str(paid_this),
            'last_month': str(paid_prev),
            'delta_pct': delta_pct,
        }
        if collection_rate is not None:
            insights.append(
                _insight(
                    code='collection_rate',
                    severity='low',
                    title='نسبة التحصيل',
                    message=f'Collection rate: {collection_rate}%.',
                    message_ar=f'نسبة التحصيل هذا الشهر تقريباً: {collection_rate}%.',
                    metric=collection_rate,
                    action_type='view_payments',
                    action_label='عرض المدفوعات',
                    action_path='/finance',
                )
            )
    else:
        metrics['collection_trend'] = {'label': 'not_enough_data'}

    return insights, metrics


def build_transport_insights(school) -> tuple[list[dict], dict]:
    insights: list[dict] = []
    buses = list(
        Bus.objects.filter(school=school, is_active=True).annotate(
            assigned=Count('student_assignments', filter=Q(student_assignments__status='ACTIVE'))
        )
    )
    active_buses = len(buses)
    transport_students = StudentTransport.objects.filter(school=school, status='ACTIVE').count()
    without = (
        Student.objects.filter(school=school, status='ACTIVE')
        .exclude(transport_assignments__status='ACTIVE')
        .count()
    )

    utilization = []
    near = 0
    under = 0
    for bus in buses:
        if not bus.capacity:
            continue
        pct = int(bus.assigned / bus.capacity * 100)
        utilization.append(
            {'bus_number': bus.bus_number, 'assigned': bus.assigned, 'capacity': bus.capacity, 'pct': pct}
        )
        if pct >= 90:
            near += 1
            insights.append(
                _insight(
                    code=f'bus_capacity_{bus.id}',
                    severity='high',
                    title='سعة الحافلة',
                    message=f'Bus {bus.bus_number} is at {pct}% capacity ({bus.assigned}/{bus.capacity}).',
                    message_ar=f'الحافلة {bus.bus_number} وصلت إلى {pct}% من السعة ({bus.assigned}/{bus.capacity}).',
                    metric={'bus': bus.bus_number, 'pct': pct},
                    action_type='view_bus',
                    action_label='عرض الحافلة',
                    action_path='/transport',
                )
            )
        elif pct <= 40 and bus.assigned > 0:
            under += 1
            insights.append(
                _insight(
                    code=f'bus_underutilized_{bus.id}',
                    severity='low',
                    title='سعة غير مستغلة',
                    message=f'Bus {bus.bus_number} has significant unused capacity ({pct}%).',
                    message_ar=f'الحافلة {bus.bus_number} لديها سعة غير مستغلة بشكل ملحوظ ({pct}%).',
                    metric={'bus': bus.bus_number, 'pct': pct},
                    action_type='view_bus',
                    action_label='عرض النقل',
                    action_path='/transport',
                )
            )

    if without:
        insights.append(
            _insight(
                code='no_transport',
                severity='low',
                title='بدون نقل',
                message=f'{without} students do not have transportation assigned.',
                message_ar=f'{without} طالب بدون نقل مدرسي.',
                metric=without,
                action_type='view_transport',
                action_label='عرض النقل',
                action_path='/transport',
            )
        )

    metrics = {
        'active_buses': active_buses,
        'transport_students': transport_students,
        'students_without_transport': without,
        'buses_near_capacity': near,
        'underutilized_buses': under,
        'utilization': utilization,
    }
    return insights, metrics


def build_cross_module_insights(school, today) -> list[dict]:
    insights: list[dict] = []
    month_start, _, _, _ = _month_bounds(today)

    if not (school_has_feature(school, 'attendance') and school_has_feature(school, 'transport')):
        pass
    else:
        repeated_ids = set(
            Attendance.objects.filter(school=school, date__gte=month_start, status='ABSENT')
            .values('student_id')
            .annotate(c=Count('id'))
            .filter(c__gte=3)
            .values_list('student_id', flat=True)
        )
        transport_repeated = StudentTransport.objects.filter(
            school=school, status='ACTIVE', student_id__in=repeated_ids
        ).count()
        if transport_repeated:
            insights.append(
                _insight(
                    code='transport_repeated_absence',
                    severity='medium',
                    title='تقاطع النقل والغياب',
                    message=(
                        f'{transport_repeated} students assigned to transport '
                        'also have repeated absences this month. These groups overlap.'
                    ),
                    message_ar=(
                        f'{transport_repeated} طالب مسجّلون في النقل لديهم غياب متكرر هذا الشهر. '
                        'هذه المجموعات متداخلة.'
                    ),
                    metric=transport_repeated,
                    action_type='view_attendance',
                    action_label='عرض الحضور',
                    action_path='/attendance',
                )
            )

    if school_has_feature(school, 'attendance') and school_has_feature(school, 'accounting'):
        repeated_ids = set(
            Attendance.objects.filter(school=school, date__gte=month_start, status='ABSENT')
            .values('student_id')
            .annotate(c=Count('id'))
            .filter(c__gte=3)
            .values_list('student_id', flat=True)
        )
        overdue_ids = set()
        for fee in Fee.objects.filter(school=school, due_date__lt=today, student_id__in=repeated_ids).prefetch_related(
            'payments'
        ):
            remaining = fee.amount - sum((p.amount for p in fee.payments.all()), Decimal('0'))
            if remaining > 0:
                overdue_ids.add(fee.student_id)
        overlap = len(overdue_ids)
        if overlap:
            insights.append(
                _insight(
                    code='overdue_and_absent',
                    severity='medium',
                    title='تقاطع الرسوم والغياب',
                    message=(
                        f'{overlap} students with overdue balances also have repeated absences. '
                        'These groups overlap.'
                    ),
                    message_ar=(
                        f'{overlap} طالب لديهم أرصدة متأخرة وغياب متكرر أيضاً. هذه المجموعات متداخلة.'
                    ),
                    metric=overlap,
                    action_type='view_payments',
                    action_label='عرض المستحقات',
                    action_path='/finance',
                )
            )

    return insights


    return insights


def build_timetable_insights(school) -> tuple[list[dict], dict]:
    """Unscheduled weekly lessons and draft conflict hints for managers."""
    insights: list[dict] = []
    metrics: dict = {
        'unscheduled_lessons': 0,
        'conflict_errors': 0,
        'has_published': False,
    }
    if not school_has_feature(school, 'timetable'):
        return insights, metrics

    from apps.timetable.models import Timetable, TimetableStatus
    from apps.timetable.services import validate_timetable

    published = (
        Timetable.objects.filter(school=school, status=TimetableStatus.PUBLISHED)
        .order_by('-published_at')
        .first()
    )
    draft = (
        Timetable.objects.filter(school=school, status=TimetableStatus.DRAFT)
        .order_by('-updated_at')
        .first()
    )
    target = draft or published
    if not target:
        return insights, metrics

    metrics['has_published'] = published is not None
    report = validate_timetable(target)
    missing = sum(
        max(0, w.get('meta', {}).get('required', 0) - w.get('meta', {}).get('scheduled', 0))
        for w in report.get('warnings', [])
        if w.get('code') == 'requirement_incomplete'
    )
    metrics['unscheduled_lessons'] = missing
    metrics['conflict_errors'] = len(report.get('errors', []))

    if missing > 0:
        insights.append(
            _insight(
                code='timetable_unscheduled',
                severity='medium',
                title='حصص أسبوعية غير مجدولة',
                message=f'{missing} weekly lessons are still unscheduled.',
                message_ar=f'⚠ {missing} حصة أسبوعية ما زالت غير مجدولة.',
                metric=missing,
                action_type='view_timetable',
                action_label='فتح الجدول',
                action_path='/timetable',
            )
        )
    if report.get('errors'):
        insights.append(
            _insight(
                code='timetable_conflicts',
                severity='high',
                title='تعارضات في الجدول',
                message=f'{len(report["errors"])} timetable conflicts.',
                message_ar=f'يوجد {len(report["errors"])} تعارض في الجدول الدراسي.',
                metric=len(report['errors']),
                action_type='view_timetable',
                action_label='مراجعة التعارضات',
                action_path='/timetable',
            )
        )
    return insights, metrics


SEVERITY_RANK = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


def build_smart_center(school, membership=None) -> dict:
    """Compose role-aware Smart School Center payload."""
    today = timezone.localdate()
    role = membership.role if membership else None
    can_finance = bool(
        membership
        and role_has_permission(membership.role, Permission.FINANCE_VIEW)
        and school_has_feature(school, 'accounting')
    )

    # Best-effort subscription warnings are emitted from /subscriptions/me/
    # (not on every dashboard load) to keep Smart Center responsive.

    sections: dict = {
        'overview': {},
        'attendance': {},
        'academic': {},
        'financial': {},
        'transport': {},
        'alerts': [],
        'trends': {},
    }
    all_insights: list[dict] = []

    is_teacher = role == Role.TEACHER
    is_parent = role == Role.PARENT
    is_accountant = role == Role.ACCOUNTANT

    if school_has_feature(school, 'attendance') and not is_parent:
        att_insights, att_metrics = build_attendance_insights(school, today)
        sections['attendance'] = att_metrics
        if not is_accountant:
            all_insights.extend(att_insights)
        sections['trends']['attendance'] = att_metrics.get('absence_trend')

    if school_has_feature(school, 'grades') and not is_accountant and not is_parent:
        ac_insights, ac_metrics = build_academic_insights(school, today)
        sections['academic'] = ac_metrics
        all_insights.extend(ac_insights)
        sections['trends']['academic'] = ac_metrics.get('term_trend')

    if can_finance and not is_teacher and not is_parent:
        fin_insights, fin_metrics = build_financial_insights(school, today)
        sections['financial'] = {
            **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in fin_metrics.items()}
        }
        all_insights.extend(fin_insights)
        sections['trends']['financial'] = fin_metrics.get('collection_trend')

    if school_has_feature(school, 'transport') and not is_accountant:
        tr_insights, tr_metrics = build_transport_insights(school)
        sections['transport'] = tr_metrics
        if not is_parent:
            all_insights.extend(tr_insights)

    if (
        school_has_feature(school, 'timetable')
        and not is_teacher
        and not is_parent
        and not is_accountant
        and membership
        and role_has_permission(membership.role, Permission.TIMETABLE_VIEW)
    ):
        tt_insights, tt_metrics = build_timetable_insights(school)
        sections['timetable'] = tt_metrics
        all_insights.extend(tt_insights)

    if not is_teacher and not is_parent:
        all_insights.extend(build_cross_module_insights(school, today))

    # Subscription alert for owners/admins
    if membership and membership.role in {Role.SCHOOL_OWNER, Role.SUPER_ADMIN, Role.SCHOOL_ADMIN}:
        try:
            sub = school.subscription
            sub.refresh_status()
            days = sub.days_remaining
            if days < 0 or sub.status == 'EXPIRED':
                all_insights.append(
                    _insight(
                        code='subscription_expired',
                        severity='critical',
                        title='انتهاء الاشتراك',
                        message='Subscription has expired.',
                        message_ar='انتهى اشتراك المدرسة. يرجى التجديد.',
                        metric=days,
                        action_type='view_subscription',
                        action_label='إدارة الاشتراك',
                        action_path='/subscription',
                    )
                )
            elif days <= 14:
                all_insights.append(
                    _insight(
                        code='subscription_expiring',
                        severity='high' if days <= 7 else 'medium',
                        title='قرب انتهاء الاشتراك',
                        message=f'Subscription expires in {days} days.',
                        message_ar=f'ينتهي الاشتراك خلال {days} يوماً.',
                        metric=days,
                        action_type='view_subscription',
                        action_label='تجديد الاشتراك',
                        action_path='/subscription',
                    )
                )
        except Exception:
            pass

    all_insights.sort(key=lambda i: SEVERITY_RANK.get(i.get('severity', 'low'), 9))
    sections['alerts'] = all_insights
    sections['overview'] = {
        'needs_attention_count': len([i for i in all_insights if i['severity'] in ('critical', 'high')]),
        'role': role,
    }
    return {
        'insights': all_insights,
        'sections': sections,
        'generated_at': timezone.now().isoformat(),
    }
