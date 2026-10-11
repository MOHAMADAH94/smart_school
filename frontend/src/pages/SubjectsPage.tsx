import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { classesApi, subjectsApi, teachersApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';
import { isSchoolManager } from '../utils/roles';

export function SubjectsPage() {
  const { schoolContext } = useAuth();
  const role = schoolContext?.membership?.role;
  const isTeacher = role === 'TEACHER';
  const isManager = isSchoolManager(role);
  const canManage = isManager && (schoolContext?.permissions ?? []).includes('subjects.manage');
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: '', code: '', description: '' });
  const [showForm, setShowForm] = useState(false);
  const [showAssign, setShowAssign] = useState(false);
  const [assignForm, setAssignForm] = useState({ teacher: '', subject: '', classroom: '' });
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['subjects'],
    queryFn: () => subjectsApi.list(),
  });

  const teachers = useQuery({
    queryKey: ['teachers'],
    queryFn: () => teachersApi.list(),
    enabled: canManage,
  });

  const classrooms = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms(),
    enabled: canManage,
  });

  const assignments = useQuery({
    queryKey: ['teaching-assignments'],
    queryFn: () => subjectsApi.listAssignments(),
  });

  const myClasses = useQuery({
    queryKey: ['my-classes'],
    queryFn: () => teachersApi.myClasses(),
    enabled: isTeacher,
  });

  const createMutation = useMutation({
    mutationFn: () => subjectsApi.create(form),
    onSuccess: async () => {
      setShowForm(false);
      setForm({ name: '', code: '', description: '' });
      setError('');
      await qc.invalidateQueries({ queryKey: ['subjects'] });
    },
    onError: () => setError('تعذر إضافة المادة.'),
  });

  const assignMutation = useMutation({
    mutationFn: () =>
      subjectsApi.createAssignment({
        teacher: Number(assignForm.teacher),
        subject: Number(assignForm.subject),
        classroom: Number(assignForm.classroom),
      }),
    onSuccess: async () => {
      setShowAssign(false);
      setAssignForm({ teacher: '', subject: '', classroom: '' });
      setError('');
      await qc.invalidateQueries({ queryKey: ['teaching-assignments'] });
      await qc.invalidateQueries({ queryKey: ['my-classes'] });
    },
    onError: () => setError('تعذر ربط المعلم بالمادة. قد يكون الربط موجوداً مسبقاً.'),
  });

  const removeAssignMutation = useMutation({
    mutationFn: (id: number) => subjectsApi.removeAssignment(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['teaching-assignments'] });
      await qc.invalidateQueries({ queryKey: ['my-classes'] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  function onAssign(e: FormEvent) {
    e.preventDefault();
    assignMutation.mutate();
  }

  if (isTeacher) {
    const myAssignments = myClasses.data?.assignments ?? assignments.data?.results ?? [];
    const mySubjects = data?.results ?? [];

    return (
      <div className="page">
        <header className="page-header">
          <h2>موادي</h2>
          <p className="muted">المواد والفصول المسندة إليك فقط</p>
        </header>

        <div className="panel table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>المادة</th>
                <th>الفصل</th>
              </tr>
            </thead>
            <tbody>
              {myAssignments.map(
                (a: {
                  id: number;
                  subject_name?: string;
                  classroom_name?: string;
                  subject?: number;
                  classroom?: number;
                }) => (
                  <tr key={a.id}>
                    <td>{a.subject_name || `مادة #${a.subject}`}</td>
                    <td>{a.classroom_name || `فصل #${a.classroom}`}</td>
                  </tr>
                ),
              )}
              {myAssignments.length === 0 && (
                <tr>
                  <td colSpan={2} className="muted">
                    لا توجد مواد مسندة لك بعد.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {mySubjects.length > 0 && (
          <div className="panel table-wrap">
            <h3>تفاصيل المواد</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>الرمز</th>
                  <th>الاسم</th>
                </tr>
              </thead>
              <tbody>
                {mySubjects.map((s) => (
                  <tr key={s.id}>
                    <td>{s.code}</td>
                    <td>{s.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>المواد الدراسية</h2>
          <p className="muted">تعريف المواد وربطها بالمعلمين والفصول</p>
        </div>
        {canManage && (
          <div className="row-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setShowAssign(true)}>
              ربط معلم بمادة
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
              إضافة مادة
            </button>
          </div>
        )}
      </header>

      {error && <div className="alert error">{error}</div>}

      {showForm && canManage && (
        <form className="panel form-grid" onSubmit={onSubmit}>
          <h3>مادة جديدة</h3>
          <label>
            الرمز *
            <input
              required
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
            />
          </label>
          <label>
            الاسم *
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label className="full">
            الوصف
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit">
              حفظ
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setShowForm(false)}>
              إلغاء
            </button>
          </div>
        </form>
      )}

      {showAssign && canManage && (
        <form className="panel form-grid" onSubmit={onAssign}>
          <h3>ربط معلم بمادة وفصل</h3>
          <label>
            المعلم *
            <select
              required
              value={assignForm.teacher}
              onChange={(e) => setAssignForm({ ...assignForm, teacher: e.target.value })}
            >
              <option value="">اختر المعلم</option>
              {(teachers.data?.results ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.full_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            المادة *
            <select
              required
              value={assignForm.subject}
              onChange={(e) => setAssignForm({ ...assignForm, subject: e.target.value })}
            >
              <option value="">اختر المادة</option>
              {(data?.results ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            الفصل *
            <select
              required
              value={assignForm.classroom}
              onChange={(e) => setAssignForm({ ...assignForm, classroom: e.target.value })}
            >
              <option value="">اختر الفصل</option>
              {(classrooms.data?.results ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={assignMutation.isPending}>
              ربط
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setShowAssign(false)}>
              إلغاء
            </button>
          </div>
        </form>
      )}

      <div className="panel table-wrap">
        <h3>المواد</h3>
        {isLoading ? (
          <p className="muted">جاري التحميل...</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>الرمز</th>
                <th>الاسم</th>
                <th>الوصف</th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((s) => (
                <tr key={s.id}>
                  <td>{s.code}</td>
                  <td>{s.name}</td>
                  <td>{s.description || '—'}</td>
                </tr>
              ))}
              {(data?.results ?? []).length === 0 && (
                <tr>
                  <td colSpan={3} className="muted">
                    لا توجد مواد بعد.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel table-wrap">
        <h3>ربط المعلمين بالمواد</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>المعلم</th>
              <th>المادة</th>
              <th>الفصل</th>
              {canManage && <th>إجراءات</th>}
            </tr>
          </thead>
          <tbody>
            {(assignments.data?.results ?? []).map(
              (a: {
                id: number;
                teacher_name: string;
                subject_name: string;
                classroom_name: string;
              }) => (
                <tr key={a.id}>
                  <td>{a.teacher_name}</td>
                  <td>{a.subject_name}</td>
                  <td>{a.classroom_name}</td>
                  {canManage && (
                    <td>
                      <button
                        type="button"
                        className="link-btn danger"
                        onClick={() => {
                          if (confirm('إلغاء هذا الربط؟')) removeAssignMutation.mutate(a.id);
                        }}
                      >
                        إلغاء الربط
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
            {(assignments.data?.results ?? []).length === 0 && (
              <tr>
                <td colSpan={canManage ? 4 : 3} className="muted">
                  لا توجد روابط بعد. استخدم «ربط معلم بمادة».
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
