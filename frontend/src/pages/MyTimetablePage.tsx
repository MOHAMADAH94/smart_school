import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { timetableApi, type TimetableEntry } from '../api/resources';

const DAY_LABELS: Record<number, string> = {
  0: 'الأحد',
  1: 'الإثنين',
  2: 'الثلاثاء',
  3: 'الأربعاء',
  4: 'الخميس',
  5: 'الجمعة',
  6: 'السبت',
};

export function MyTimetablePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-timetable'],
    queryFn: () => timetableApi.my(),
  });

  const byDay = useMemo(() => {
    const map = new Map<number, TimetableEntry[]>();
    for (const e of data?.entries ?? []) {
      const list = map.get(e.day) ?? [];
      list.push(e);
      map.set(e.day, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => (a.period_number ?? 0) - (b.period_number ?? 0));
    }
    return map;
  }, [data]);

  if (isLoading) return <div className="page muted">جاري التحميل...</div>;

  const days = [...byDay.keys()].sort((a, b) => a - b);

  return (
    <div className="page">
      <header className="page-header print-hide">
        <div>
          <h2>جدولي</h2>
          <p className="muted">
            {data?.timetable
              ? `${data.timetable.name} — ${data.timetable.academic_year}`
              : 'لا يوجد جدول منشور حالياً'}
          </p>
        </div>
        <button type="button" className="btn btn-ghost" onClick={() => window.print()}>
          طباعة
        </button>
      </header>

      {!data?.timetable && (
        <section className="panel">
          <p className="muted">عند نشر إدارة المدرسة للجدول سيظهر هنا تلقائياً.</p>
        </section>
      )}

      {days.map((day) => (
        <section key={day} className="panel">
          <h3>{DAY_LABELS[day] || `يوم ${day}`}</h3>
          <ul className="timeline-list">
            {(byDay.get(day) ?? []).map((e) => (
              <li key={e.id}>
                <strong>
                  {String(e.start_time || '').slice(0, 5) || `حصة ${e.period_number}`}
                </strong>
                <span>
                  {e.classroom_name} — {e.subject_name}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
