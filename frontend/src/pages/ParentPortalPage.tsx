import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { parentsApi, timetableApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';
import { formatNumber } from '../utils/format';

type SectionKey = 'grades' | 'attendance' | 'transport' | 'fees' | 'timetable';

const DAY_LABELS: Record<number, string> = {
  0: 'الأحد',
  1: 'الإثنين',
  2: 'الثلاثاء',
  3: 'الأربعاء',
  4: 'الخميس',
  5: 'الجمعة',
  6: 'السبت',
};

const attendanceLabel: Record<string, string> = {
  PRESENT: 'حاضر',
  ABSENT: 'غائب',
  LATE: 'متأخر',
  EXCUSED: 'بعذر',
};

function formatScore(cell: { score: number | string | null; max_score: number | string } | null | undefined) {
  if (!cell || cell.score == null || cell.score === '') return '—';
  return `${cell.score}`;
}

export function ParentPortalPage() {
  const { schoolContext } = useAuth();
  const features = new Set(schoolContext?.features ?? []);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['my-children'],
    queryFn: () => parentsApi.myChildren(),
  });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [section, setSection] = useState<SectionKey>('grades');
  const [termId, setTermId] = useState<string>('');

  const children = data?.children ?? [];
  const parent = data?.parent;

  const activeChild = useMemo(() => {
    if (!children.length) return null;
    const found = children.find((c: { id: number }) => c.id === selectedId);
    return found ?? children[0];
  }, [children, selectedId]);

  const childTimetable = useQuery({
    queryKey: ['child-timetable', activeChild?.id],
    queryFn: () => timetableApi.child(activeChild!.id),
    enabled: !!activeChild?.id && section === 'timetable' && features.has('timetable'),
  });

  const terms = activeChild?.gradebook?.terms ?? [];
  const activeTerm = useMemo(() => {
    if (!terms.length) return null;
    if (termId) {
      const found = terms.find((t: { term_id: number }) => String(t.term_id) === termId);
      if (found) return found;
    }
    return terms.find((t: { is_current: boolean }) => t.is_current) ?? terms[0];
  }, [terms, termId]);

  const sections: { key: SectionKey; label: string }[] = [
    { key: 'grades', label: 'الدرجات' },
    { key: 'attendance', label: 'الحضور والغياب' },
    { key: 'transport', label: 'النقل' },
    { key: 'fees', label: 'الرسوم' },
    ...(features.has('timetable')
      ? ([{ key: 'timetable' as const, label: 'الجدول الدراسي' }] as const)
      : []),
  ];

  if (isLoading) return <div className="page muted">جاري التحميل...</div>;

  if (isError) {
    return (
      <div className="page">
        <header className="page-header">
          <h2>أبنائي</h2>
        </header>
        <section className="panel">
          <p className="alert error">
            تعذر تحميل بيانات الأبناء. {(error as Error)?.message || 'حاول مرة أخرى.'}
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>أبنائي</h2>
        <p className="muted">
          {parent ? `مرحباً ${parent.name}` : 'بوابة ولي الأمر'} — الحضور والدرجات والمتابعة
        </p>
      </header>

      {children.length === 0 && (
        <section className="panel">
          <p className="muted">لا يوجد أبناء مرتبطون بهذا الحساب.</p>
        </section>
      )}

      {children.length > 0 && (
        <>
          <div className="child-tabs" role="tablist" aria-label="الأبناء">
            {children.map((child: any) => {
              const active = activeChild?.id === child.id;
              return (
                <button
                  key={child.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`child-tab${active ? ' active' : ''}`}
                  onClick={() => {
                    setSelectedId(child.id);
                    setTermId('');
                    setSection('grades');
                  }}
                >
                  <strong>{child.full_name}</strong>
                  <span>{child.classroom_name || 'بدون فصل'}</span>
                </button>
              );
            })}
          </div>

          {activeChild && (
            <section className="panel child-card">
              <div className="row-between child-card-head">
                <div>
                  <h3>{activeChild.full_name}</h3>
                  <p className="muted">
                    {activeChild.student_code}
                    {activeChild.classroom_name ? ` · ${activeChild.classroom_name}` : ''}
                  </p>
                </div>
                <Link className="btn btn-ghost" to={`/students/${activeChild.id}`}>
                  الملف الكامل
                </Link>
              </div>

              <div className="tabs">
                {sections.map((s) => (
                  <button
                    key={s.key}
                    type="button"
                    className={section === s.key ? 'tab active' : 'tab'}
                    onClick={() => setSection(s.key)}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              {section === 'grades' && (
                <div className="gradebook-block">
                  <div className="row-between" style={{ alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h4 style={{ margin: 0 }}>كشف الدرجات</h4>
                    {terms.length > 0 && (
                      <select
                        value={String(activeTerm?.term_id ?? '')}
                        onChange={(e) => setTermId(e.target.value)}
                        aria-label="الفصل الدراسي"
                      >
                        {terms.map((t: any) => (
                          <option key={t.term_id} value={t.term_id}>
                            {t.term_name} ({t.academic_year})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  {!activeTerm || !(activeTerm.columns?.length > 0) ? (
                    <p className="muted">لا توجد تقييمات مسجّلة لهذا الفصل الدراسي بعد.</p>
                  ) : (
                    <div className="table-wrap grade-matrix-wrap">
                      <table className="data-table grade-matrix">
                        <thead>
                          <tr>
                            <th className="sticky-col">المادة</th>
                            {activeTerm.columns.map((col: any) => (
                              <th key={col.key} title={col.assessment_type_label}>
                                {col.label !== col.assessment_type_label && (
                                  <span className="col-type">{col.assessment_type_label}</span>
                                )}
                                <span className="col-label">{col.label}</span>
                              </th>
                            ))}
                            <th>المتوسط</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeTerm.rows.map((row: any) => (
                            <tr key={row.subject_id}>
                              <td className="sticky-col subject-cell">{row.subject_name}</td>
                              {activeTerm.columns.map((col: any) => {
                                const cell = row.cells?.[col.key];
                                return (
                                  <td
                                    key={col.key}
                                    className="score-cell"
                                    title={
                                      cell
                                        ? `${cell.name || col.label}${
                                            cell.max_score != null ? ` / ${cell.max_score}` : ''
                                          }`
                                        : undefined
                                    }
                                  >
                                    {formatScore(cell)}
                                    {cell?.score != null && cell?.max_score != null && (
                                      <span className="max-hint">/{cell.max_score}</span>
                                    )}
                                  </td>
                                );
                              })}
                              <td className="score-cell avg-cell">
                                {formatNumber(row.average)}
                              </td>
                            </tr>
                          ))}
                          {activeTerm.rows.length === 0 && (
                            <tr>
                              <td colSpan={(activeTerm.columns?.length ?? 0) + 2} className="muted">
                                لا توجد مواد لهذا الفصل.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {section === 'attendance' && (
                <div>
                  <div className="detail-grid" style={{ marginBottom: '1rem' }}>
                    <div>
                      <span className="muted">حضور اليوم</span>
                      <strong>
                        {attendanceLabel[activeChild.today_status] ||
                          activeChild.today_status ||
                          '—'}
                      </strong>
                    </div>
                    <div>
                      <span className="muted">حاضر</span>
                      <strong>{activeChild.attendance_summary?.present ?? 0}</strong>
                    </div>
                    <div>
                      <span className="muted">غائب</span>
                      <strong>{activeChild.attendance_summary?.absent ?? 0}</strong>
                    </div>
                    <div>
                      <span className="muted">متأخر</span>
                      <strong>{activeChild.attendance_summary?.late ?? 0}</strong>
                    </div>
                  </div>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>التاريخ</th>
                          <th>الحالة</th>
                          <th>ملاحظات</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(activeChild.attendance ?? []).map((a: any) => (
                          <tr key={a.id}>
                            <td>{a.date}</td>
                            <td>{attendanceLabel[a.status] || a.status}</td>
                            <td>{a.notes || '—'}</td>
                          </tr>
                        ))}
                        {(activeChild.attendance ?? []).length === 0 && (
                          <tr>
                            <td colSpan={3} className="muted">
                              لا سجلات حضور بعد.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {section === 'transport' && (
                <div>
                  {activeChild.transport ? (
                    <div className="detail-grid">
                      <div>
                        <span className="muted">الحافلة</span>
                        <strong>{activeChild.transport.bus_number}</strong>
                      </div>
                      <div>
                        <span className="muted">المسار</span>
                        <strong>{activeChild.transport.route_name}</strong>
                      </div>
                      <div>
                        <span className="muted">الاستلام</span>
                        <strong>{activeChild.transport.pickup_location || '—'}</strong>
                      </div>
                      <div>
                        <span className="muted">التوصيل</span>
                        <strong>{activeChild.transport.dropoff_location || '—'}</strong>
                      </div>
                      <div>
                        <span className="muted">الرسوم الشهرية</span>
                        <strong>{activeChild.transport.monthly_fee}</strong>
                      </div>
                      <div>
                        <span className="muted">الحالة</span>
                        <strong>{activeChild.transport.status}</strong>
                      </div>
                    </div>
                  ) : (
                    <p className="muted">لا يوجد نقل معيّن لهذا الطالب.</p>
                  )}
                </div>
              )}

              {section === 'timetable' && (
                <div>
                  {childTimetable.isLoading && <p className="muted">جاري تحميل الجدول...</p>}
                  {!childTimetable.isLoading && !childTimetable.data?.timetable && (
                    <p className="muted">لا يوجد جدول منشور لهذا الفصل بعد.</p>
                  )}
                  {childTimetable.data?.timetable && (
                    <>
                      <p className="muted" style={{ marginBottom: '0.75rem' }}>
                        {childTimetable.data.classroom_name} — {childTimetable.data.timetable.name}
                      </p>
                      {(childTimetable.data.working_days ?? [0, 1, 2, 3, 4]).map((day: number) => {
                        const dayEntries = (childTimetable.data.entries ?? [])
                          .filter((e: any) => e.day === day)
                          .sort(
                            (a: any, b: any) => (a.period_number ?? 0) - (b.period_number ?? 0),
                          );
                        if (!dayEntries.length) return null;
                        return (
                          <div key={day} style={{ marginBottom: '1rem' }}>
                            <h4 style={{ margin: '0 0 0.4rem' }}>{DAY_LABELS[day] || day}</h4>
                            <ul className="timeline-list">
                              {dayEntries.map((e: any) => (
                                <li key={e.id}>
                                  <strong>
                                    {String(e.start_time || '').slice(0, 5) ||
                                      `حصة ${e.period_number}`}
                                  </strong>
                                  <span>
                                    {e.subject_name}
                                    {e.teacher_name ? ` — ${e.teacher_name}` : ''}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        );
                      })}
                    </>
                  )}
                </div>
              )}

              {section === 'fees' && (
                <div>
                  <div className="detail-grid" style={{ marginBottom: '1rem' }}>
                    <div>
                      <span className="muted">إجمالي الرسوم</span>
                      <strong>{activeChild.finance?.total_fees ?? 0}</strong>
                    </div>
                    <div>
                      <span className="muted">المدفوع</span>
                      <strong>{activeChild.finance?.paid ?? 0}</strong>
                    </div>
                    <div>
                      <span className="muted">المتبقي</span>
                      <strong>{activeChild.finance?.remaining ?? 0}</strong>
                    </div>
                  </div>

                  <h4 style={{ marginBottom: '0.5rem' }}>الرسوم</h4>
                  <div className="table-wrap" style={{ marginBottom: '1rem' }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>البند</th>
                          <th>السنة</th>
                          <th>المبلغ</th>
                          <th>المدفوع</th>
                          <th>المتبقي</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(activeChild.fees ?? []).map((f: any) => (
                          <tr key={f.id}>
                            <td>{f.title}</td>
                            <td>{f.academic_year || '—'}</td>
                            <td>{f.amount}</td>
                            <td>{f.paid_amount ?? '—'}</td>
                            <td>{f.remaining_amount ?? '—'}</td>
                          </tr>
                        ))}
                        {(activeChild.fees ?? []).length === 0 && (
                          <tr>
                            <td colSpan={5} className="muted">
                              لا توجد رسوم مسجّلة.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  <h4 style={{ marginBottom: '0.5rem' }}>المدفوعات</h4>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>التاريخ</th>
                          <th>المبلغ</th>
                          <th>الطريقة</th>
                          <th>المرجع</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(activeChild.payments ?? []).map((p: any) => (
                          <tr key={p.id}>
                            <td>{p.payment_date}</td>
                            <td>{p.amount}</td>
                            <td>{p.method || '—'}</td>
                            <td>{p.reference || '—'}</td>
                          </tr>
                        ))}
                        {(activeChild.payments ?? []).length === 0 && (
                          <tr>
                            <td colSpan={4} className="muted">
                              لا توجد مدفوعات بعد.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
