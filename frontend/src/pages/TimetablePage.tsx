import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState, type DragEvent, type FormEvent } from 'react';
import { api } from '../api/client';
import { classesApi, subjectsApi, timetableApi, type Timetable, type TimetableEntry } from '../api/resources';
import { useAuth } from '../context/AuthContext';

const DAY_LABELS: Record<number, string> = {
  0: 'الأحد',
  1: 'الإثنين',
  2: 'الثلاثاء',
  3: 'الأربعاء',
  4: 'الخميس',
  5: 'الجمعة',
  6: 'السبت',
};

const STATUS_LABEL: Record<string, string> = {
  DRAFT: 'مسودة',
  PUBLISHED: 'منشور',
  ARCHIVED: 'مؤرشف',
};

type Tab = 'list' | 'requirements' | 'grid' | 'school';

export function TimetablePage() {
  const qc = useQueryClient();
  const { schoolContext } = useAuth();
  const canManage = (schoolContext?.permissions ?? []).includes('timetable.manage');
  const [tab, setTab] = useState<Tab>('list');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [classroomId, setClassroomId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [createForm, setCreateForm] = useState({
    name: 'الجدول الرئيسي',
    academic_year: '2025-2026',
    period_duration_minutes: '45',
  });
  const [reqForm, setReqForm] = useState({
    classroom: '',
    subject: '',
    teaching_assignment: '',
    lessons_per_week: '4',
    max_lessons_per_day: '2',
  });
  const [dragEntryId, setDragEntryId] = useState<number | null>(null);

  const timetables = useQuery({
    queryKey: ['timetables'],
    queryFn: () => timetableApi.list(),
  });
  const rows: Timetable[] = timetables.data?.results ?? [];
  const selected = rows.find((t) => t.id === selectedId) ?? rows[0] ?? null;
  const activeId = selected?.id ?? null;

  const classrooms = useQuery({
    queryKey: ['classrooms-tt'],
    queryFn: () => classesApi.listClassrooms(),
  });
  const subjects = useQuery({
    queryKey: ['subjects-tt'],
    queryFn: () => subjectsApi.list(),
  });
  const assignments = useQuery({
    queryKey: ['assignments-tt'],
    queryFn: () => subjectsApi.listAssignments(),
  });

  const requirements = useQuery({
    queryKey: ['tt-requirements', activeId],
    queryFn: () => timetableApi.listRequirements({ timetable: String(activeId) }),
    enabled: !!activeId,
  });

  const grid = useQuery({
    queryKey: ['tt-grid', activeId, classroomId],
    queryFn: () =>
      timetableApi.grid(activeId!, classroomId ? { classroom: classroomId } : undefined),
    enabled: !!activeId && (tab === 'grid' || tab === 'school'),
  });

  const validation = useQuery({
    queryKey: ['tt-validate', activeId],
    queryFn: () => timetableApi.validate(activeId!),
    enabled: !!activeId && canManage,
  });

  const classroomRows = classrooms.data?.results ?? [];
  const assignmentRows = assignments.data?.results ?? [];
  const reqRows = requirements.data?.results ?? [];
  const periods = (grid.data?.periods ?? []).slice().sort((a, b) => a.period_number - b.period_number);
  const workingDays: number[] = grid.data?.working_days ?? selected?.working_days ?? [0, 1, 2, 3, 4];
  const entries: TimetableEntry[] = grid.data?.entries ?? [];

  const filteredAssignments = useMemo(() => {
    return assignmentRows.filter((a: any) => {
      if (reqForm.classroom && String(a.classroom) !== reqForm.classroom) return false;
      if (reqForm.subject && String(a.subject) !== reqForm.subject) return false;
      return true;
    });
  }, [assignmentRows, reqForm.classroom, reqForm.subject]);

  const entryMap = useMemo(() => {
    const map = new Map<string, TimetableEntry>();
    for (const e of entries) {
      if (classroomId && String(e.classroom) !== classroomId) continue;
      map.set(`${e.day}-${e.period}`, e);
    }
    return map;
  }, [entries, classroomId]);

  const createTt = useMutation({
    mutationFn: () =>
      timetableApi.create({
        name: createForm.name,
        academic_year: createForm.academic_year,
        period_duration_minutes: Number(createForm.period_duration_minutes) || 45,
        working_days: [0, 1, 2, 3, 4],
      }),
    onSuccess: async (data) => {
      setMessage('تم إنشاء الجدول مع الحصص الافتراضية.');
      setError('');
      setSelectedId(data.id);
      await qc.invalidateQueries({ queryKey: ['timetables'] });
    },
    onError: () => setError('تعذر إنشاء الجدول.'),
  });

  const addRequirement = useMutation({
    mutationFn: () =>
      timetableApi.createRequirement({
        timetable: activeId!,
        classroom: Number(reqForm.classroom),
        subject: Number(reqForm.subject),
        teaching_assignment: Number(reqForm.teaching_assignment),
        lessons_per_week: Number(reqForm.lessons_per_week),
        max_lessons_per_day: reqForm.max_lessons_per_day
          ? Number(reqForm.max_lessons_per_day)
          : null,
      }),
    onSuccess: async () => {
      setMessage('تمت إضافة المتطلب الأسبوعي.');
      setError('');
      setReqForm((f) => ({ ...f, teaching_assignment: '', lessons_per_week: '4' }));
      await qc.invalidateQueries({ queryKey: ['tt-requirements', activeId] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || 'تعذر إضافة المتطلب. تحقق من تكليف المعلم.');
    },
  });

  const generate = useMutation({
    mutationFn: () =>
      timetableApi.generate(activeId!, {
        apply: true,
        replace_existing: true,
      }),
    onSuccess: async (data) => {
      if (data.success) {
        setMessage(
          `✓ ${data.message_ar} — حصص مقترحة: ${data.stats?.proposed_lessons ?? 0}`,
        );
      } else {
        setError(
          `${data.message_ar}\n${(data.problems || []).map((p: any) => p.message_ar).join('\n')}`,
        );
      }
      await qc.invalidateQueries({ queryKey: ['tt-grid'] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
      await qc.invalidateQueries({ queryKey: ['tt-requirements', activeId] });
    },
    onError: (err: any) => setError(err?.response?.data?.detail || 'فشل التوليد.'),
  });

  const publish = useMutation({
    mutationFn: () => timetableApi.publish(activeId!),
    onSuccess: async () => {
      setMessage('تم نشر الجدول. تم إشعار المعلمين المتأثرين.');
      setError('');
      await qc.invalidateQueries({ queryKey: ['timetables'] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
    },
    onError: (err: any) =>
      setError(err?.response?.data?.detail || 'لا يمكن النشر مع وجود تعارضات.'),
  });

  const archive = useMutation({
    mutationFn: () => timetableApi.archive(activeId!),
    onSuccess: async () => {
      setMessage('تمت أرشفة الجدول.');
      await qc.invalidateQueries({ queryKey: ['timetables'] });
    },
  });

  const removeEntry = useMutation({
    mutationFn: (id: number) => timetableApi.removeEntry(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['tt-grid'] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
    },
  });

  const moveEntry = useMutation({
    mutationFn: ({ id, day, period }: { id: number; day: number; period: number }) =>
      timetableApi.moveEntry(id, { day, period }),
    onSuccess: async () => {
      setError('');
      await qc.invalidateQueries({ queryKey: ['tt-grid'] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
    },
    onError: (err: any) => {
      const conflicts = err?.response?.data?.conflicts;
      setError(
        Array.isArray(conflicts)
          ? conflicts.join(' — ')
          : err?.response?.data?.detail || 'تعذر نقل الحصة (تعارض).',
      );
    },
  });

  const placeFromRequirement = useMutation({
    mutationFn: async (payload: {
      day: number;
      period: number;
      classroom: number;
      subject: number;
      teaching_assignment: number;
    }) =>
      timetableApi.createEntry({
        timetable: activeId!,
        ...payload,
      }),
    onSuccess: async () => {
      setError('');
      await qc.invalidateQueries({ queryKey: ['tt-grid'] });
      await qc.invalidateQueries({ queryKey: ['tt-validate', activeId] });
      await qc.invalidateQueries({ queryKey: ['tt-requirements', activeId] });
    },
    onError: (err: any) => {
      const conflicts = err?.response?.data?.conflicts;
      setError(
        Array.isArray(conflicts)
          ? conflicts.join(' — ')
          : err?.response?.data?.detail || 'تعذر وضع الحصة.',
      );
    },
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    createTt.mutate();
  }

  function onAddReq(e: FormEvent) {
    e.preventDefault();
    if (!activeId) return;
    addRequirement.mutate();
  }

  function onDragStart(entryId: number) {
    setDragEntryId(entryId);
  }

  function onDropCell(day: number, periodId: number) {
    if (!canManage || selected?.status !== 'DRAFT') return;
    if (dragEntryId) {
      moveEntry.mutate({ id: dragEntryId, day, period: periodId });
      setDragEntryId(null);
      return;
    }
  }

  function allowDrop(e: DragEvent) {
    e.preventDefault();
  }

  const isDraft = selected?.status === 'DRAFT';

  return (
    <div className="page">
      <header className="page-header print-hide">
        <div>
          <h2>الجدول الدراسي</h2>
          <p className="muted">تكوين الحصص، المتطلبات الأسبوعية، التوليد، والمراجعة قبل النشر</p>
        </div>
        {selected && (
          <div className="header-actions">
            <button type="button" className="btn btn-ghost" onClick={() => window.print()}>
              طباعة
            </button>
          </div>
        )}
      </header>

      {(message || error) && (
        <div className={`alert ${error ? 'error' : ''} print-hide`} style={{ whiteSpace: 'pre-wrap' }}>
          {error || message}
        </div>
      )}

      <div className="tabs print-hide">
        {(
          [
            ['list', 'الجداول'],
            ['requirements', 'المتطلبات'],
            ['grid', 'محرر الجدول'],
            ['school', 'عرض المدرسة'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={tab === key ? 'tab active' : 'tab'}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'list' && (
        <div className="split-panels">
          <section className="panel">
            <h3>الجداول الحالية</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>الاسم</th>
                  <th>العام</th>
                  <th>الحالة</th>
                  <th>حصص / متطلبات</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((t) => (
                  <tr key={t.id} className={t.id === activeId ? 'selected-row' : ''}>
                    <td>{t.name}</td>
                    <td>{t.academic_year}</td>
                    <td>{STATUS_LABEL[t.status] || t.status}</td>
                    <td>
                      {t.entries_count ?? 0} / {t.requirements_count ?? 0}
                    </td>
                    <td className="actions-cell">
                      <button type="button" className="link-btn" onClick={() => setSelectedId(t.id)}>
                        اختيار
                      </button>
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => {
                          setSelectedId(t.id);
                          setTab('grid');
                        }}
                      >
                        فتح المحرر
                      </button>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      لا يوجد جداول بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          {canManage && (
            <section className="panel">
              <h3>إنشاء جدول جديد</h3>
              <form className="stack-form" onSubmit={onCreate}>
                <label>
                  الاسم
                  <input
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    required
                  />
                </label>
                <label>
                  العام الدراسي
                  <input
                    value={createForm.academic_year}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, academic_year: e.target.value })
                    }
                    required
                  />
                </label>
                <label>
                  مدة الحصة (دقيقة)
                  <input
                    type="number"
                    min={20}
                    value={createForm.period_duration_minutes}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, period_duration_minutes: e.target.value })
                    }
                  />
                </label>
                <p className="muted small">
                  أيام العمل الافتراضية: الأحد–الخميس، مع 7 حصص واستراحة متوسطة.
                </p>
                <button type="submit" className="btn btn-primary" disabled={createTt.isPending}>
                  إنشاء
                </button>
              </form>

              {selected && canManage && (
                <div className="stack-form" style={{ marginTop: '1.5rem' }}>
                  <h3>إجراءات: {selected.name}</h3>
                  <p className="muted">
                    الحالة: {STATUS_LABEL[selected.status]} — تحقق قبل النشر من اكتمال المتطلبات.
                  </p>
                  {validation.data && (
                    <ul className="insight-list">
                      {(validation.data.errors || []).map((e: any, i: number) => (
                        <li key={`e-${i}`} className="danger-text">
                          ✕ {e.message_ar}
                        </li>
                      ))}
                      {(validation.data.warnings || []).map((w: any, i: number) => (
                        <li key={`w-${i}`} className="warn-text">
                          ⚠ {w.message_ar}
                        </li>
                      ))}
                      {validation.data.ok && <li className="ok-text">✓ جاهز للنشر</li>}
                    </ul>
                  )}
                  <div className="btn-row">
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={!isDraft || generate.isPending}
                      onClick={() => {
                        if (
                          selected.entries_count &&
                          !window.confirm('استبدال الحصص الحالية بالاقتراح المولَّد؟')
                        ) {
                          return;
                        }
                        generate.mutate();
                      }}
                    >
                      توليد جدول مقترح
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={!isDraft || publish.isPending}
                      onClick={() => {
                        if (!window.confirm('نشر الجدول وإشعار المعلمين؟')) return;
                        publish.mutate();
                      }}
                    >
                      نشر
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={selected.status === 'ARCHIVED' || archive.isPending}
                      onClick={() => archive.mutate()}
                    >
                      أرشفة
                    </button>
                  </div>
                </div>
              )}
            </section>
          )}
        </div>
      )}

      {tab === 'requirements' && (
        <div className="split-panels">
          <section className="panel">
            <h3>المتطلبات الأسبوعية {selected ? `— ${selected.name}` : ''}</h3>
            {!selected && <p className="muted">اختر جدولاً أولاً من تبويب الجداول.</p>}
            {selected && (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الفصل</th>
                    <th>المادة</th>
                    <th>المعلم</th>
                    <th>مطلوب</th>
                    <th>مجدول</th>
                    <th>حد/يوم</th>
                  </tr>
                </thead>
                <tbody>
                  {reqRows.map((r: any) => (
                    <tr key={r.id}>
                      <td>{r.classroom_name}</td>
                      <td>{r.subject_name}</td>
                      <td>{r.teacher_name}</td>
                      <td>{r.lessons_per_week}</td>
                      <td>{r.scheduled_count}</td>
                      <td>{r.max_lessons_per_day ?? '—'}</td>
                    </tr>
                  ))}
                  {reqRows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        لا متطلبات بعد.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </section>

          {canManage && selected && isDraft && (
            <section className="panel">
              <h3>إضافة متطلب</h3>
              <form className="stack-form" onSubmit={onAddReq}>
                <label>
                  الفصل
                  <select
                    value={reqForm.classroom}
                    onChange={(e) => setReqForm({ ...reqForm, classroom: e.target.value })}
                    required
                  >
                    <option value="">اختر</option>
                    {classroomRows.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  المادة
                  <select
                    value={reqForm.subject}
                    onChange={(e) => setReqForm({ ...reqForm, subject: e.target.value })}
                    required
                  >
                    <option value="">اختر</option>
                    {(subjects.data?.results ?? []).map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  تكليف المعلم
                  <select
                    value={reqForm.teaching_assignment}
                    onChange={(e) =>
                      setReqForm({ ...reqForm, teaching_assignment: e.target.value })
                    }
                    required
                  >
                    <option value="">اختر تكليفاً صالحاً</option>
                    {filteredAssignments.map((a: any) => (
                      <option key={a.id} value={a.id}>
                        {a.teacher_name || a.teacher} — {a.subject_name || a.subject} —{' '}
                        {a.classroom_name || a.classroom}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  حصص / أسبوع
                  <input
                    type="number"
                    min={1}
                    value={reqForm.lessons_per_week}
                    onChange={(e) => setReqForm({ ...reqForm, lessons_per_week: e.target.value })}
                    required
                  />
                </label>
                <label>
                  حد أقصى / يوم
                  <input
                    type="number"
                    min={1}
                    value={reqForm.max_lessons_per_day}
                    onChange={(e) =>
                      setReqForm({ ...reqForm, max_lessons_per_day: e.target.value })
                    }
                  />
                </label>
                <button type="submit" className="btn btn-primary" disabled={addRequirement.isPending}>
                  إضافة
                </button>
              </form>
            </section>
          )}
        </div>
      )}

      {(tab === 'grid' || tab === 'school') && selected && (
        <section className="panel timetable-panel">
          <div className="timetable-toolbar print-hide">
            <div>
              <strong>{selected.name}</strong>
              <span className="muted"> — {STATUS_LABEL[selected.status]}</span>
            </div>
            {tab === 'grid' && (
              <label>
                الفصل
                <select value={classroomId} onChange={(e) => setClassroomId(e.target.value)}>
                  <option value="">اختر فصلاً</option>
                  {classroomRows.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {tab === 'school' && (
              <p className="muted small">عرض كل الفصول — اسحب للتحقق من تعارضات المعلمين.</p>
            )}
          </div>

          {tab === 'grid' && !classroomId && (
            <p className="muted">اختر فصلاً لعرض/تعديل جدوله الأسبوعي.</p>
          )}

          {(tab === 'school' || classroomId) && (
            <div className="timetable-scroll">
              <table className="timetable-grid data-table">
                <thead>
                  <tr>
                    <th>الحصة</th>
                    {workingDays.map((d) => (
                      <th key={d}>{DAY_LABELS[d] || d}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {periods.map((p) => (
                    <tr key={p.id} className={p.is_break ? 'break-row' : ''}>
                      <td className="period-cell">
                        <strong>{p.label || `الحصة ${p.period_number}`}</strong>
                        <small>
                          {String(p.start_time).slice(0, 5)} – {String(p.end_time).slice(0, 5)}
                        </small>
                      </td>
                      {workingDays.map((day) => {
                        if (p.is_break) {
                          return (
                            <td key={`${day}-${p.id}`} className="break-cell">
                              استراحة
                            </td>
                          );
                        }
                        if (tab === 'school') {
                          const cellEntries = entries.filter(
                            (e) => e.day === day && e.period === p.id,
                          );
                          return (
                            <td key={`${day}-${p.id}`} className="tt-cell">
                              {cellEntries.map((e) => (
                                <div key={e.id} className="lesson-card compact">
                                  <strong>{e.subject_name}</strong>
                                  <span>{e.classroom_name}</span>
                                  <span className="muted">{e.teacher_name}</span>
                                </div>
                              ))}
                            </td>
                          );
                        }
                        const entry = entryMap.get(`${day}-${p.id}`);
                        return (
                          <td
                            key={`${day}-${p.id}`}
                            className="tt-cell droppable"
                            onDragOver={allowDrop}
                            onDrop={() => onDropCell(day, p.id)}
                          >
                            {entry ? (
                              <div
                                className="lesson-card"
                                draggable={canManage && isDraft}
                                onDragStart={() => onDragStart(entry.id)}
                              >
                                <strong>{entry.subject_name}</strong>
                                <span>{entry.teacher_name}</span>
                                {canManage && isDraft && (
                                  <button
                                    type="button"
                                    className="link-btn danger-text"
                                    onClick={() => removeEntry.mutate(entry.id)}
                                  >
                                    حذف
                                  </button>
                                )}
                              </div>
                            ) : (
                              canManage &&
                              isDraft &&
                              classroomId && (
                                <select
                                  className="table-select"
                                  defaultValue=""
                                  onChange={(e) => {
                                    const req = reqRows.find(
                                      (r: any) => String(r.id) === e.target.value,
                                    );
                                    if (!req) return;
                                    placeFromRequirement.mutate({
                                      day,
                                      period: p.id,
                                      classroom: Number(classroomId),
                                      subject: req.subject,
                                      teaching_assignment: req.teaching_assignment,
                                    });
                                    e.target.value = '';
                                  }}
                                >
                                  <option value="">+ حصة</option>
                                  {reqRows
                                    .filter((r: any) => String(r.classroom) === classroomId)
                                    .map((r: any) => (
                                      <option key={r.id} value={r.id}>
                                        {r.subject_name} — {r.teacher_name}
                                      </option>
                                    ))}
                                </select>
                              )
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
