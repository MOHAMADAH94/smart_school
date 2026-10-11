import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

type Insight = {
  code: string;
  severity: string;
  title?: string;
  message?: string;
  message_ar?: string;
  metric?: unknown;
  action_label?: string | null;
  action_path?: string | null;
};

const severityRank: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function DashboardPage() {
  const { schoolContext, user } = useAuth();
  const school = schoolContext?.school;
  const role = schoolContext?.membership?.role;
  const features = new Set(schoolContext?.features ?? []);
  const permissions = new Set(schoolContext?.permissions ?? []);

  const stats = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => (await api.get('/dashboard/stats/')).data,
  });
  const insights = useQuery({
    queryKey: ['dashboard-insights'],
    queryFn: async () => (await api.get('/dashboard/insights/')).data,
  });

  const s = stats.data;
  const list: Insight[] = [...(insights.data?.insights ?? [])].sort(
    (a, b) => (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9),
  );
  const sections = insights.data?.sections ?? {};
  const needsAttention = list.filter((i) => i.severity === 'critical' || i.severity === 'high');
  const rest = list.filter((i) => i.severity !== 'critical' && i.severity !== 'high');

  const showFinance =
    features.has('accounting') && permissions.has('finance.view') && role !== 'TEACHER' && role !== 'PARENT';
  const isTeacher = role === 'TEACHER';
  const isParent = role === 'PARENT';
  const isAccountant = role === 'ACCOUNTANT';

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h2>مركز المدرسة الذكية</h2>
          <p className="muted">
            مرحباً {user?.first_name || user?.username}
            {school ? ` — ${school.name}` : ''}
          </p>
        </div>
      </header>

      <section className="panel needs-attention">
        <h3>يحتاج إلى انتباه</h3>
        <p className="muted">أهم التنبيهات أولاً — ثم المقاييس والتفاصيل.</p>
        {needsAttention.length === 0 && (
          <p className="empty-state">لا توجد تنبيهات حرجة حالياً.</p>
        )}
        <div className="insight-list">
          {needsAttention.map((i) => (
            <InsightCard key={i.code} insight={i} />
          ))}
        </div>
      </section>

      {!isParent && (
        <section className="stats-grid">
          {!isAccountant && (
            <>
              <article className="stat-tile">
                <span>الطلاب</span>
                <strong>{s?.total_students ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>المعلمون</span>
                <strong>{s?.total_teachers ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>الفصول</span>
                <strong>{s?.total_classrooms ?? 0}</strong>
              </article>
            </>
          )}
          {features.has('attendance') && !isAccountant && (
            <>
              <article className="stat-tile">
                <span>حضور اليوم</span>
                <strong>{s?.today_attendance ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>غياب اليوم</span>
                <strong>{s?.today_absences ?? 0}</strong>
              </article>
              {sections.attendance?.monthly_attendance_rate != null && (
                <article className="stat-tile">
                  <span>نسبة الحضور الشهرية</span>
                  <strong>{sections.attendance.monthly_attendance_rate}%</strong>
                </article>
              )}
            </>
          )}
          {features.has('transport') && !isAccountant && !isTeacher && (
            <>
              <article className="stat-tile">
                <span>الحافلات</span>
                <strong>{s?.total_buses ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>طلاب النقل</span>
                <strong>{s?.total_buses != null ? s?.students_using_transport ?? 0 : 0}</strong>
              </article>
            </>
          )}
          {showFinance && (
            <>
              <article className="stat-tile">
                <span>الرسوم</span>
                <strong>{s?.total_fees ?? sections.financial?.total_fees ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>المدفوع</span>
                <strong>{s?.paid ?? sections.financial?.paid ?? 0}</strong>
              </article>
              <article className="stat-tile">
                <span>المتبقي</span>
                <strong>{s?.outstanding ?? sections.financial?.outstanding ?? 0}</strong>
              </article>
              {sections.financial?.collection_rate != null && (
                <article className="stat-tile">
                  <span>نسبة التحصيل</span>
                  <strong>{sections.financial.collection_rate}%</strong>
                </article>
              )}
            </>
          )}
        </section>
      )}

      {isTeacher && (
        <section className="panel">
          <h3>مساحة المعلم</h3>
          <div className="row-actions">
            <Link className="btn" to="/attendance">
              حضور اليوم
            </Link>
            <Link className="btn ghost" to="/grades">
              الدرجات
            </Link>
            <Link className="btn ghost" to="/notifications">
              إشعاراتي
            </Link>
          </div>
        </section>
      )}

      {isParent && (
        <section className="panel">
          <h3>بوابة ولي الأمر</h3>
          <div className="row-actions">
            <Link className="btn" to="/parent">
              أبنائي
            </Link>
            <Link className="btn ghost" to="/notifications">
              الإشعارات
            </Link>
          </div>
        </section>
      )}

      {rest.length > 0 && (
        <section className="panel">
          <h3>رؤى إضافية</h3>
          <div className="insight-list">
            {rest.map((i) => (
              <InsightCard key={i.code} insight={i} />
            ))}
          </div>
        </section>
      )}

      {sections.trends && Object.keys(sections.trends).length > 0 && (
        <section className="panel">
          <h3>الاتجاهات</h3>
          <ul className="simple-list">
            {Object.entries(sections.trends).map(([key, value]) => {
              const v = value as { label?: string; delta?: number; delta_pct?: number } | null;
              if (!v || v.label === 'not_enough_data') {
                return (
                  <li key={key}>
                    {trendLabel(key)}: لا توجد بيانات كافية للمقارنة
                  </li>
                );
              }
              return (
                <li key={key}>
                  {trendLabel(key)}
                  {v.delta != null ? `: تغير ${v.delta}` : ''}
                  {v.delta_pct != null ? `: ${v.delta_pct}%` : ''}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className={`insight-card severity-${insight.severity}`}>
      <div className="insight-card-head">
        <strong>{insight.title || insight.code}</strong>
        <span className="severity-tag">{severityAr(insight.severity)}</span>
      </div>
      <p>{insight.message_ar || insight.message}</p>
      {insight.action_path && insight.action_label && (
        <Link className="btn ghost" to={insight.action_path}>
          {insight.action_label}
        </Link>
      )}
    </article>
  );
}

function severityAr(s: string) {
  return (
    {
      critical: 'حرج',
      high: 'مرتفع',
      medium: 'متوسط',
      low: 'منخفض',
    }[s] || s
  );
}

function trendLabel(key: string) {
  return (
    {
      attendance: 'الحضور',
      academic: 'الأكاديمي',
      financial: 'المالي',
    }[key] || key
  );
}
