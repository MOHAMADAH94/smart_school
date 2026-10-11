from django.db.models import Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.models import Attendance
from apps.dashboard.insights import build_smart_center
from apps.finance.models import Expense, Fee, Payment
from apps.schools.permissions import HasSchoolMembership, HasSchoolPermission, IsAuthenticatedAndActive
from apps.schools.roles import Permission
from apps.students.models import Student
from apps.subscriptions.services import get_enabled_features, school_has_feature
from apps.teachers.models import Teacher
from apps.transport.models import Bus, StudentTransport


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]
    required_permission = Permission.DASHBOARD_VIEW

    def get(self, request):
        school = request.school
        features = get_enabled_features(school)
        today = timezone.localdate()

        data = {
            'total_students': Student.objects.filter(school=school, status='ACTIVE').count(),
            'total_teachers': Teacher.objects.filter(school=school, status='ACTIVE').count(),
            'total_classrooms': school.classrooms.count(),
            'features': features,
        }

        if school_has_feature(school, 'attendance'):
            today_qs = Attendance.objects.filter(school=school, date=today)
            data['today_attendance'] = today_qs.exclude(status='ABSENT').count()
            data['today_absences'] = today_qs.filter(status='ABSENT').count()

        if school_has_feature(school, 'transport'):
            data['total_buses'] = Bus.objects.filter(school=school, is_active=True).count()
            data['students_using_transport'] = StudentTransport.objects.filter(
                school=school, status='ACTIVE'
            ).count()

        if school_has_feature(school, 'accounting'):
            total_fees = Fee.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
            paid = Payment.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
            expenses = Expense.objects.filter(school=school).aggregate(s=Sum('amount'))['s'] or 0
            data.update(
                {
                    'total_fees': total_fees,
                    'paid': paid,
                    'outstanding': total_fees - paid,
                    'expenses': expenses,
                    'revenue': paid - expenses,
                }
            )

        return Response(data)


class SmartInsightsView(APIView):
    """
    Smart School Center — needs-attention insights with actions.
    Calculated (not persisted) via dashboard.insights rule engine.
    """

    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]
    required_permission = Permission.DASHBOARD_VIEW

    def get(self, request):
        payload = build_smart_center(request.school, membership=getattr(request, 'membership', None))
        return Response(payload)


class DashboardSectionView(APIView):
    """Optional section detail: attendance | academic | financial | transport."""

    permission_classes = [IsAuthenticatedAndActive, HasSchoolMembership, HasSchoolPermission]
    required_permission = Permission.DASHBOARD_VIEW

    def get(self, request, section: str):
        payload = build_smart_center(request.school, membership=getattr(request, 'membership', None))
        sections = payload.get('sections', {})
        if section not in sections:
            return Response({'detail': 'قسم غير معروف.'}, status=404)
        return Response({'section': section, 'data': sections[section], 'insights': [
            i for i in payload.get('insights', [])
            if section in i.get('code', '') or (
                section == 'financial' and i.get('action_path') == '/finance'
            ) or (
                section == 'attendance' and i.get('action_path') == '/attendance'
            ) or (
                section == 'transport' and i.get('action_path') == '/transport'
            ) or (
                section == 'academic' and i.get('action_path') == '/grades'
            )
        ]})
