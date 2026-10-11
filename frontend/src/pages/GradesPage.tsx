import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { formatNumber } from '../utils/format';
import {
  classesApi,
  gradesApi,
  studentsApi,
  subjectsApi,
  teachersApi,
} from '../api/resources';
import { useAuth } from '../context/AuthContext';
import { isSchoolManager } from '../utils/roles';

function formatScore(cell: { score: number | string | null; max_score: number | string } | null | undefined) {
  if (!cell || cell.score == null || cell.score === '') return '—';
  return `${cell.score}`;
}

export function GradesPage() {
  const { schoolContext } = useAuth();
  const role = schoolContext?.membership?.role;
  const isTeacher = role === 'TEACHER';
  const isManager = isSchoolManager(role);
  const canEnterGrades = (schoolContext?.permissions ?? []).includes('grades.manage');
  const canSetupAssessments = isManager && canEnterGrades;
  const qc = useQueryClient();

  const [mode, setMode] = useState<'entry' | 'book'>('entry');
  const [classroomId, setClassroomId] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [termId, setTermId] = useState('');
  const [assessmentId, setAssessmentId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [bookTermId, setBookTermId] = useState('');
  const [scores, setScores] = useState<Record<number, string>>({});
  const [error, setError] = useState('');
  const [showAssessmentForm, setShowAssessmentForm] = useState(false);
  const [showTermForm, setShowTermForm] = useState(false);
  const [assessmentForm, setAssessmentForm] = useState({
    name: '',
    assessment_type: 'QUIZ',
    max_score: '100',
    date: new Date().toISOString().slice(0, 10),
  });
  const [termForm, setTermForm] = useState({
    name: '',
    academic_year: new Date().getFullYear().toString(),
    is_current: true,
  });

  const classrooms = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms({ page_size: '200' }),
    enabled: !isTeacher,
  });
  const myClasses = useQuery({
    queryKey: ['my-classes'],
    queryFn: () => teachersApi.myClasses(),
    enabled: isTeacher,
  });
  const subjects = useQuery({
    queryKey: ['subjects'],
    queryFn: () => subjectsApi.list({ page_size: '200' }),
    enabled: !isTeacher,
  });
  const terms = useQuery({
    queryKey: ['grade-terms'],
    queryFn: () => gradesApi.listTerms(),
  });

  const classroomOptions = useMemo(() => {
    if (isTeacher) {
      return (myClasses.data?.classrooms ?? []).map((c: { id: number; name: string }) => ({
        id: c.id,
        name: c.name,
      }));
    }
    return classrooms.data?.results ?? [];
  }, [isTeacher, myClasses.data, classrooms.data]);

  const subjectOptions = useMemo(() => {
    if (isTeacher) {
      const assignments = myClasses.data?.assignments ?? [];
      const map = new Map<number, { id: number; name: string }>();
      for (const a of assignments) {
        const sid = a.subject_id ?? a.subject;
        const cid = a.classroom_id ?? a.classroom;
        if (!classroomId || String(cid) === classroomId) {
          map.set(sid, { id: sid, name: a.subject_name || `مادة #${sid}` });
        }
      }
      return Array.from(map.values());
    }
    return subjects.data?.results ?? [];
  }, [isTeacher, myClasses.data, subjects.data, classroomId]);

  const assignmentAllowed = useMemo(() => {
    if (!isTeacher || !classroomId || !subjectId) return true;
    const assignments = myClasses.data?.assignments ?? [];
    return assignments.some(
      (a: { classroom_id?: number; subject_id?: number; classroom?: number; subject?: number }) =>
        String(a.classroom_id ?? a.classroom) === classroomId &&
        String(a.subject_id ?? a.subject) === subjectId,
    );
  }, [isTeacher, classroomId, subjectId, myClasses.data]);

  const assessments = useQuery({
    queryKey: ['assessments', classroomId, subjectId, termId],
    queryFn: () =>
      gradesApi.listAssessments({
        page_size: '200',
        ...(classroomId ? { classroom: classroomId } : {}),
        ...(subjectId ? { subject: subjectId } : {}),
        ...(termId ? { term: termId } : {}),
      }),
    enabled: mode === 'entry' && Boolean(classroomId && subjectId && assignmentAllowed),
  });

  const students = useQuery({
    queryKey: ['grade-students', classroomId],
    queryFn: () =>
      studentsApi.list({ classroom: classroomId, status: 'ACTIVE', page_size: '200' }),
    enabled: Boolean(classroomId),
  });

  const existingGrades = useQuery({
    queryKey: ['grades-for-assessment', assessmentId],
    queryFn: () => gradesApi.list({ assessment: assessmentId, page_size: '200' }),
    enabled: mode === 'entry' && Boolean(assessmentId),
  });

  const report = useQuery({
    queryKey: ['grades-report', classroomId, subjectId],
    queryFn: () =>
      gradesApi.report({
        ...(classroomId ? { classroom: classroomId } : {}),
        ...(subjectId ? { subject: subjectId } : {}),
      }),
    enabled: mode === 'entry',
  });

  const gradebook = useQuery({
    queryKey: ['student-gradebook', studentId],
    queryFn: () => gradesApi.gradebook({ student: studentId }),
    enabled: mode === 'book' && Boolean(studentId),
  });

  const studentList = students.data?.results ?? [];
  const assessmentList = assessments.data?.results ?? [];
  const selectedAssessment = assessmentList.find((a: { id: number }) => String(a.id) === assessmentId);

  const bookTerms = gradebook.data?.gradebook?.terms ?? [];
  const activeBookTerm = useMemo(() => {
    if (!bookTerms.length) return null;
    if (bookTermId) {
      const found = bookTerms.find((t: { term_id: number }) => String(t.term_id) === bookTermId);
      if (found) return found;
    }
    return bookTerms.find((t: { is_current: boolean }) => t.is_current) ?? bookTerms[0];
  }, [bookTerms, bookTermId]);

  useEffect(() => {
    if (!assessmentId) {
      setScores({});
      return;
    }
    const next: Record<number, string> = {};
    for (const s of studentList) next[s.id] = '';
    for (const g of existingGrades.data?.results ?? []) {
      next[g.student] = String(g.score);
    }
    setScores(next);
  }, [assessmentId, studentList, existingGrades.data]);

  useEffect(() => {
    const list = terms.data?.results ?? [];
    if (!termId && list.length) {
      const current = list.find((t: { is_current: boolean }) => t.is_current) ?? list[0];
      setTermId(String(current.id));
    }
  }, [terms.data, termId]);

  useEffect(() => {
    if (classroomId && isTeacher) {
      const stillValid = subjectOptions.some((s) => String(s.id) === subjectId);
      if (!stillValid) {
        setSubjectId('');
        setAssessmentId('');
      }
    }
  }, [classroomId, subjectOptions, subjectId, isTeacher]);

  useEffect(() => {
    setStudentId('');
    setBookTermId('');
  }, [classroomId]);

  const createTermMutation = useMutation({
    mutationFn: () => gradesApi.createTerm(termForm),
    onSuccess: async (term: { id: number }) => {
      setShowTermForm(false);
      setTermId(String(term.id));
      await qc.invalidateQueries({ queryKey: ['grade-terms'] });
    },
    onError: () => setError('تعذر إنشاء الفصل الدراسي.'),
  });

  const createAssessmentMutation = useMutation({
    mutationFn: () =>
      gradesApi.createAssessment({
        name: assessmentForm.name,
        assessment_type: assessmentForm.assessment_type,
        max_score: assessmentForm.max_score,
        date: assessmentForm.date || null,
        classroom: Number(classroomId),
        subject: Number(subjectId),
        term: Number(termId),
      }),
    onSuccess: async (a: { id: number }) => {
      setShowAssessmentForm(false);
      setAssessmentForm({
        name: '',
        assessment_type: 'QUIZ',
        max_score: '100',
        date: new Date().toISOString().slice(0, 10),
      });
      setAssessmentId(String(a.id));
      await qc.invalidateQueries({ queryKey: ['assessments'] });
    },
    onError: () => setError('تعذر إنشاء التقييم.'),
  });

  const saveScoresMutation = useMutation({
    mutationFn: async () => {
      const records = Object.entries(scores)
        .filter(([, score]) => score !== '')
        .map(([student_id, score]) => ({
          student_id: Number(student_id),
          score,
        }));
      if (!records.length) throw new Error('empty');
      return gradesApi.bulk({ assessment_id: Number(assessmentId), records });
    },
    onSuccess: async () => {
      setError('');
      await qc.invalidateQueries({ queryKey: ['grades-for-assessment', assessmentId] });
      await qc.invalidateQueries({ queryKey: ['grades-report'] });
      await qc.invalidateQueries({ queryKey: ['student-gradebook'] });
      alert('تم حفظ الدرجات');
    },
    onError: () => setError('تعذر حفظ الدرجات.'),
  });

  function onCreateAssessment(e: FormEvent) {
    e.preventDefault();
    createAssessmentMutation.mutate();
  }

  function onCreateTerm(e: FormEvent) {
    e.preventDefault();
    createTermMutation.mutate();
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>الدرجات</h2>
          <p className="muted">
            {isTeacher
              ? 'إدخال درجات طلاب فصولك وعرض كشف الدرجات كأولياء الأمور'
              : 'إنشاء تقييمات وإدخال الدرجات وعرض كشف الدرجات'}
          </p>
        </div>
        {canEnterGrades && mode === 'entry' && (
          <button
            type="button"
            className="btn btn-primary"
            disabled={!assessmentId || !assignmentAllowed || saveScoresMutation.isPending}
            onClick={() => saveScoresMutation.mutate()}
          >
            حفظ الدرجات
          </button>
        )}
      </header>

      <div className="tabs">
        <button
          type="button"
          className={mode === 'entry' ? 'tab active' : 'tab'}
          onClick={() => setMode('entry')}
        >
          إدخال الدرجات
        </button>
        <button
          type="button"
          className={mode === 'book' ? 'tab active' : 'tab'}
          onClick={() => setMode('book')}
        >
          كشف الدرجات
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {mode === 'entry' && (
        <>
          <section className="stats-grid">
            <article className="stat-tile">
              <span>متوسط الطلاب</span>
              <strong>{formatNumber(report.data?.student_average)}</strong>
            </article>
            <article className="stat-tile">
              <span>متوسط المواد</span>
              <strong>{formatNumber(report.data?.subject_average)}</strong>
            </article>
            <article className="stat-tile">
              <span>متوسط الفصول</span>
              <strong>{formatNumber(report.data?.classroom_average)}</strong>
            </article>
          </section>

          <div className="toolbar">
            <select
              value={classroomId}
              onChange={(e) => {
                setClassroomId(e.target.value);
                setSubjectId('');
                setAssessmentId('');
              }}
            >
              <option value="">اختر الفصل</option>
              {classroomOptions.map((c: { id: number; name: string }) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <select
              value={subjectId}
              onChange={(e) => {
                setSubjectId(e.target.value);
                setAssessmentId('');
              }}
            >
              <option value="">اختر المادة</option>
              {subjectOptions.map((s: { id: number; name: string }) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <select value={termId} onChange={(e) => setTermId(e.target.value)}>
              <option value="">الفصل الدراسي</option>
              {(terms.data?.results ?? []).map(
                (t: { id: number; name: string; academic_year: string }) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.academic_year})
                  </option>
                ),
              )}
            </select>
            <select value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}>
              <option value="">اختر التقييم</option>
              {assessmentList.map(
                (a: {
                  id: number;
                  name: string;
                  max_score: string;
                  assessment_type_label?: string;
                }) => (
                  <option key={a.id} value={a.id}>
                    {a.assessment_type_label ? `${a.assessment_type_label}: ` : ''}
                    {a.name} (من {a.max_score})
                  </option>
                ),
              )}
            </select>
            {canSetupAssessments && (
              <>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={!classroomId || !subjectId || !termId}
                  onClick={() => setShowAssessmentForm(true)}
                >
                  تقييم جديد
                </button>
                <button type="button" className="btn btn-ghost" onClick={() => setShowTermForm(true)}>
                  فصل دراسي
                </button>
              </>
            )}
          </div>

          {showTermForm && canSetupAssessments && (
            <form className="panel form-grid" onSubmit={onCreateTerm}>
              <h3>فصل دراسي جديد</h3>
              <label>
                الاسم *
                <input
                  required
                  value={termForm.name}
                  onChange={(e) => setTermForm({ ...termForm, name: e.target.value })}
                  placeholder="الفصل الأول"
                />
              </label>
              <label>
                السنة الأكاديمية *
                <input
                  required
                  value={termForm.academic_year}
                  onChange={(e) => setTermForm({ ...termForm, academic_year: e.target.value })}
                />
              </label>
              <label>
                الحالي؟
                <select
                  value={termForm.is_current ? '1' : '0'}
                  onChange={(e) => setTermForm({ ...termForm, is_current: e.target.value === '1' })}
                >
                  <option value="1">نعم</option>
                  <option value="0">لا</option>
                </select>
              </label>
              <div className="form-actions">
                <button className="btn btn-primary" type="submit">
                  حفظ
                </button>
                <button className="btn btn-ghost" type="button" onClick={() => setShowTermForm(false)}>
                  إلغاء
                </button>
              </div>
            </form>
          )}

          {showAssessmentForm && canSetupAssessments && (
            <form className="panel form-grid" onSubmit={onCreateAssessment}>
              <h3>تقييم جديد</h3>
              <label>
                اسم التقييم *
                <input
                  required
                  value={assessmentForm.name}
                  onChange={(e) => setAssessmentForm({ ...assessmentForm, name: e.target.value })}
                  placeholder="مذاكرة 1"
                />
              </label>
              <label>
                النوع *
                <select
                  value={assessmentForm.assessment_type}
                  onChange={(e) =>
                    setAssessmentForm({ ...assessmentForm, assessment_type: e.target.value })
                  }
                >
                  <option value="QUIZ">مذاكرة</option>
                  <option value="HOMEWORK">واجب</option>
                  <option value="MIDTERM">امتحان نصفي</option>
                  <option value="FINAL">امتحان نهائي فصلي</option>
                  <option value="OTHER">أخرى</option>
                </select>
              </label>
              <label>
                الدرجة القصوى *
                <input
                  required
                  type="number"
                  min="1"
                  step="0.01"
                  value={assessmentForm.max_score}
                  onChange={(e) => setAssessmentForm({ ...assessmentForm, max_score: e.target.value })}
                />
              </label>
              <label>
                التاريخ
                <input
                  type="date"
                  value={assessmentForm.date}
                  onChange={(e) => setAssessmentForm({ ...assessmentForm, date: e.target.value })}
                />
              </label>
              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  type="submit"
                  disabled={createAssessmentMutation.isPending}
                >
                  إنشاء
                </button>
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => setShowAssessmentForm(false)}
                >
                  إلغاء
                </button>
              </div>
            </form>
          )}

          <div className="panel table-wrap">
            {!classroomId || !subjectId ? (
              <p className="muted">اختر الفصل والمادة أولاً.</p>
            ) : !assignmentAllowed ? (
              <p className="muted">هذه المادة غير مسندة لك في هذا الفصل.</p>
            ) : !assessmentId ? (
              <p className="muted">اختر تقييماً لإدخال الدرجات.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>الرمز</th>
                    <th>الطالب</th>
                    <th>الدرجة {selectedAssessment ? `(من ${selectedAssessment.max_score})` : ''}</th>
                  </tr>
                </thead>
                <tbody>
                  {studentList.map((s) => (
                    <tr key={s.id}>
                      <td>{s.student_code}</td>
                      <td>{s.full_name}</td>
                      <td>
                        {canEnterGrades ? (
                          <input
                            type="number"
                            min="0"
                            max={selectedAssessment?.max_score ?? undefined}
                            step="0.01"
                            value={scores[s.id] ?? ''}
                            onChange={(e) => setScores({ ...scores, [s.id]: e.target.value })}
                            style={{ width: '8rem' }}
                          />
                        ) : (
                          scores[s.id] || '—'
                        )}
                      </td>
                    </tr>
                  ))}
                  {studentList.length === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        لا يوجد طلاب في هذا الفصل.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {mode === 'book' && (
        <section className="panel">
          <div className="toolbar" style={{ marginBottom: '1rem' }}>
            <select
              value={classroomId}
              onChange={(e) => {
                setClassroomId(e.target.value);
              }}
            >
              <option value="">اختر الفصل</option>
              {classroomOptions.map((c: { id: number; name: string }) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <select
              value={studentId}
              onChange={(e) => {
                setStudentId(e.target.value);
                setBookTermId('');
              }}
              disabled={!classroomId}
            >
              <option value="">اختر الطالب</option>
              {studentList.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name} ({s.student_code})
                </option>
              ))}
            </select>
            {bookTerms.length > 0 && (
              <select value={String(activeBookTerm?.term_id ?? '')} onChange={(e) => setBookTermId(e.target.value)}>
                {bookTerms.map((t: { term_id: number; term_name: string; academic_year: string }) => (
                  <option key={t.term_id} value={t.term_id}>
                    {t.term_name} ({t.academic_year})
                  </option>
                ))}
              </select>
            )}
          </div>

          {!classroomId || !studentId ? (
            <p className="muted">اختر الفصل ثم الطالب لعرض كشف الدرجات بنفس شكل بوابة ولي الأمر.</p>
          ) : gradebook.isLoading ? (
            <p className="muted">جاري التحميل...</p>
          ) : !activeBookTerm || !(activeBookTerm.columns?.length > 0) ? (
            <p className="muted">لا توجد تقييمات مسجّلة لهذا الطالب بعد.</p>
          ) : (
            <div className="table-wrap grade-matrix-wrap">
              <table className="data-table grade-matrix">
                <thead>
                  <tr>
                    <th className="sticky-col">المادة</th>
                    {activeBookTerm.columns.map((col: any) => (
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
                  {activeBookTerm.rows.map((row: any) => (
                    <tr key={row.subject_id}>
                      <td className="sticky-col subject-cell">{row.subject_name}</td>
                      {activeBookTerm.columns.map((col: any) => {
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
                      <td className="score-cell avg-cell">{formatNumber(row.average)}</td>
                    </tr>
                  ))}
                  {activeBookTerm.rows.length === 0 && (
                    <tr>
                      <td colSpan={(activeBookTerm.columns?.length ?? 0) + 2} className="muted">
                        لا توجد مواد لهذا الفصل.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
