import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { classesApi, type Classroom, type GradeLevel } from '../api/resources';
import { useAuth } from '../context/AuthContext';
import { isSchoolManager } from '../utils/roles';

const emptyClassForm = { name: '', grade_level: '', section: '' };

export function ClassesPage() {
  const { schoolContext } = useAuth();
  const canManage = isSchoolManager(schoolContext?.membership?.role);
  const qc = useQueryClient();

  const [gradeName, setGradeName] = useState('');
  const [classForm, setClassForm] = useState(emptyClassForm);
  const [gradeError, setGradeError] = useState('');
  const [classError, setClassError] = useState('');

  const [editGrade, setEditGrade] = useState<GradeLevel | null>(null);
  const [editGradeName, setEditGradeName] = useState('');
  const [editGradeError, setEditGradeError] = useState('');

  const [editClass, setEditClass] = useState<Classroom | null>(null);
  const [editClassForm, setEditClassForm] = useState(emptyClassForm);
  const [editClassError, setEditClassError] = useState('');

  const grades = useQuery({
    queryKey: ['grades'],
    queryFn: () => classesApi.listGrades(),
  });
  const classrooms = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms(),
  });

  const gradeList = grades.data?.results ?? [];
  const classroomList = classrooms.data?.results ?? [];
  const totalStudents = classroomList.reduce((sum, c) => sum + (c.student_count || 0), 0);

  useEffect(() => {
    const open = Boolean(editGrade || editClass);
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [editGrade, editClass]);

  const addGrade = useMutation({
    mutationFn: () =>
      classesApi.createGrade({
        name: gradeName.trim(),
        order: gradeList.length + 1,
      }),
    onSuccess: async () => {
      setGradeName('');
      setGradeError('');
      await qc.invalidateQueries({ queryKey: ['grades'] });
    },
    onError: () => setGradeError('تعذر حفظ المرحلة. تحقق من الاسم وحاول مجدداً.'),
  });

  const updateGrade = useMutation({
    mutationFn: () =>
      classesApi.updateGrade(editGrade!.id, { name: editGradeName.trim() }),
    onSuccess: async () => {
      closeGradeModal();
      await qc.invalidateQueries({ queryKey: ['grades'] });
      await qc.invalidateQueries({ queryKey: ['classrooms'] });
    },
    onError: () => setEditGradeError('تعذر تحديث المرحلة.'),
  });

  const deleteGrade = useMutation({
    mutationFn: (id: number) => classesApi.removeGrade(id),
    onSuccess: async () => {
      closeGradeModal();
      await qc.invalidateQueries({ queryKey: ['grades'] });
      await qc.invalidateQueries({ queryKey: ['classrooms'] });
    },
    onError: () => setGradeError('تعذر حذف المرحلة. قد تكون مرتبطة بفصول موجودة.'),
  });

  const addClass = useMutation({
    mutationFn: () =>
      classesApi.createClassroom({
        name: classForm.name.trim(),
        section: classForm.section.trim(),
        grade_level: Number(classForm.grade_level),
      }),
    onSuccess: async () => {
      setClassForm(emptyClassForm);
      setClassError('');
      await qc.invalidateQueries({ queryKey: ['classrooms'] });
    },
    onError: () => setClassError('تعذر حفظ الفصل. أكمل الحقول المطلوبة وحاول مجدداً.'),
  });

  const updateClass = useMutation({
    mutationFn: () =>
      classesApi.updateClassroom(editClass!.id, {
        name: editClassForm.name.trim(),
        section: editClassForm.section.trim(),
        grade_level: Number(editClassForm.grade_level),
      }),
    onSuccess: async () => {
      closeClassModal();
      await qc.invalidateQueries({ queryKey: ['classrooms'] });
    },
    onError: () => setEditClassError('تعذر تحديث الفصل.'),
  });

  const deleteClass = useMutation({
    mutationFn: (id: number) => classesApi.removeClassroom(id),
    onSuccess: async () => {
      closeClassModal();
      await qc.invalidateQueries({ queryKey: ['classrooms'] });
    },
    onError: () => setClassError('تعذر حذف الفصل. قد يكون مرتبطاً بطلاب أو تكليفات.'),
  });

  function closeGradeModal() {
    setEditGrade(null);
    setEditGradeName('');
    setEditGradeError('');
  }

  function closeClassModal() {
    setEditClass(null);
    setEditClassForm(emptyClassForm);
    setEditClassError('');
  }

  function openEditGrade(g: GradeLevel) {
    setEditGrade(g);
    setEditGradeName(g.name);
    setEditGradeError('');
  }

  function openEditClass(c: Classroom) {
    setEditClass(c);
    setEditClassForm({
      name: c.name,
      grade_level: String(c.grade_level),
      section: c.section || '',
    });
    setEditClassError('');
  }

  function submitAddGrade(e: FormEvent) {
    e.preventDefault();
    if (!gradeName.trim()) return;
    addGrade.mutate();
  }

  function submitAddClass(e: FormEvent) {
    e.preventDefault();
    if (!classForm.grade_level || !classForm.name.trim()) return;
    addClass.mutate();
  }

  function submitEditGrade(e: FormEvent) {
    e.preventDefault();
    if (!editGradeName.trim()) return;
    updateGrade.mutate();
  }

  function submitEditClass(e: FormEvent) {
    e.preventDefault();
    if (!editClassForm.grade_level || !editClassForm.name.trim()) return;
    updateClass.mutate();
  }

  return (
    <div className="page classes-page">
      <header className="page-header">
        <div>
          <h2>الفصول والمراحل</h2>
          <p className="muted">
            {canManage
              ? 'نظّم البنية الأكاديمية: مراحل أولاً، ثم الفصول والشعب'
              : 'الفصول المسندة إليك فقط'}
          </p>
        </div>
      </header>

      <section className="stats-grid classes-stats">
        <article className="stat-tile">
          <span>المراحل</span>
          <strong>{gradeList.length}</strong>
        </article>
        <article className="stat-tile">
          <span>الفصول</span>
          <strong>{classroomList.length}</strong>
        </article>
        <article className="stat-tile">
          <span>الطلاب في الفصول</span>
          <strong>{totalStudents}</strong>
        </article>
      </section>

      <div className="classes-layout">
        <section className="panel classes-side">
          <div className="section-head">
            <div>
              <h3>المراحل</h3>
              <p className="muted">الصفوف الدراسية الأساسية</p>
            </div>
          </div>

          {canManage && (
            <form className="inline-add-form" onSubmit={submitAddGrade}>
              {gradeError && <div className="alert error">{gradeError}</div>}
              <div className="inline-add-row">
                <input
                  required
                  value={gradeName}
                  onChange={(e) => setGradeName(e.target.value)}
                  placeholder="اسم مرحلة جديدة…"
                />
                <button className="btn btn-primary" type="submit" disabled={addGrade.isPending}>
                  إضافة
                </button>
              </div>
            </form>
          )}

          {gradeList.length === 0 ? (
            <p className="muted empty-hint">لا توجد مراحل بعد.</p>
          ) : (
            <ul className="manage-list">
              {gradeList.map((g) => (
                <li key={g.id}>
                  <span className="manage-list-title">{g.name}</span>
                  {canManage && (
                    <span className="row-actions">
                      <button type="button" className="link-btn" onClick={() => openEditGrade(g)}>
                        تعديل
                      </button>
                      <button
                        type="button"
                        className="link-btn danger"
                        onClick={() => {
                          if (
                            confirm(
                              `حذف المرحلة «${g.name}»؟ لا يمكن الحذف إن وُجدت فصول مرتبطة بها.`,
                            )
                          ) {
                            deleteGrade.mutate(g.id);
                          }
                        }}
                      >
                        حذف
                      </button>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel classes-main">
          <div className="section-head">
            <div>
              <h3>الفصول</h3>
              <p className="muted">الشعب المرتبطة بكل مرحلة</p>
            </div>
          </div>

          {canManage && (
            <form className="panel-inset create-card-form" onSubmit={submitAddClass}>
              <h4 className="inset-title">إضافة فصل جديد</h4>
              {classError && <div className="alert error">{classError}</div>}
              <label>
                المرحلة *
                <select
                  required
                  value={classForm.grade_level}
                  onChange={(e) => setClassForm({ ...classForm, grade_level: e.target.value })}
                  disabled={gradeList.length === 0}
                >
                  <option value="">
                    {gradeList.length === 0 ? 'أضف مرحلة أولاً' : 'اختر المرحلة'}
                  </option>
                  {gradeList.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="create-card-row">
                <label>
                  اسم الفصل *
                  <input
                    required
                    value={classForm.name}
                    onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
                    placeholder="مثال: الصف التاسع - أ"
                    disabled={gradeList.length === 0}
                  />
                </label>
                <label>
                  الشعبة
                  <input
                    value={classForm.section}
                    onChange={(e) => setClassForm({ ...classForm, section: e.target.value })}
                    placeholder="أ / ب / ج"
                    disabled={gradeList.length === 0}
                  />
                </label>
              </div>
              <div className="form-actions">
                <button
                  className="btn btn-primary"
                  type="submit"
                  disabled={addClass.isPending || gradeList.length === 0}
                >
                  {addClass.isPending ? 'جاري الحفظ…' : 'حفظ الفصل'}
                </button>
              </div>
            </form>
          )}

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>الفصل</th>
                  <th>المرحلة</th>
                  <th>الشعبة</th>
                  <th>الطلاب</th>
                  {canManage && <th>إجراءات</th>}
                </tr>
              </thead>
              <tbody>
                {classroomList.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.grade_level_name}</td>
                    <td>{c.section || '—'}</td>
                    <td>{c.student_count}</td>
                    {canManage && (
                      <td className="actions-cell">
                        <button type="button" className="link-btn" onClick={() => openEditClass(c)}>
                          تعديل
                        </button>
                        <button
                          type="button"
                          className="link-btn danger"
                          onClick={() => {
                            if (confirm(`حذف الفصل «${c.name}»؟`)) deleteClass.mutate(c.id);
                          }}
                        >
                          حذف
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                {classroomList.length === 0 && (
                  <tr>
                    <td colSpan={canManage ? 5 : 4} className="muted">
                      لا توجد فصول بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {editGrade && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeGradeModal();
          }}
        >
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="edit-grade-title">
            <div className="modal-head">
              <div>
                <h3 id="edit-grade-title">تعديل المرحلة</h3>
                <p className="muted">تحديث اسم المرحلة الدراسية</p>
              </div>
              <button type="button" className="modal-close" onClick={closeGradeModal} aria-label="إغلاق">
                ×
              </button>
            </div>
            <form className="create-card-form" onSubmit={submitEditGrade}>
              {editGradeError && <div className="alert error">{editGradeError}</div>}
              <label>
                اسم المرحلة
                <input
                  required
                  autoFocus
                  value={editGradeName}
                  onChange={(e) => setEditGradeName(e.target.value)}
                />
              </label>
              <div className="form-actions modal-actions">
                <button className="btn btn-primary" type="submit" disabled={updateGrade.isPending}>
                  {updateGrade.isPending ? 'جاري التحديث…' : 'حفظ التعديلات'}
                </button>
                <button className="btn btn-ghost" type="button" onClick={closeGradeModal}>
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editClass && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeClassModal();
          }}
        >
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="edit-class-title">
            <div className="modal-head">
              <div>
                <h3 id="edit-class-title">تعديل الفصل</h3>
                <p className="muted">تحديث بيانات الفصل والشعبة</p>
              </div>
              <button type="button" className="modal-close" onClick={closeClassModal} aria-label="إغلاق">
                ×
              </button>
            </div>
            <form className="create-card-form" onSubmit={submitEditClass}>
              {editClassError && <div className="alert error">{editClassError}</div>}
              <label>
                المرحلة *
                <select
                  required
                  value={editClassForm.grade_level}
                  onChange={(e) =>
                    setEditClassForm({ ...editClassForm, grade_level: e.target.value })
                  }
                >
                  <option value="">اختر المرحلة</option>
                  {gradeList.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="create-card-row">
                <label>
                  اسم الفصل *
                  <input
                    required
                    autoFocus
                    value={editClassForm.name}
                    onChange={(e) => setEditClassForm({ ...editClassForm, name: e.target.value })}
                  />
                </label>
                <label>
                  الشعبة
                  <input
                    value={editClassForm.section}
                    onChange={(e) =>
                      setEditClassForm({ ...editClassForm, section: e.target.value })
                    }
                    placeholder="أ / ب / ج"
                  />
                </label>
              </div>
              <div className="form-actions modal-actions">
                <button className="btn btn-primary" type="submit" disabled={updateClass.isPending}>
                  {updateClass.isPending ? 'جاري التحديث…' : 'حفظ التعديلات'}
                </button>
                <button className="btn btn-ghost" type="button" onClick={closeClassModal}>
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
