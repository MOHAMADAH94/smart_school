import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { studentsApi, teachersApi } from '../api/resources';

export function TeacherClassPage() {
  const [classroomId, setClassroomId] = useState<string>('');

  const myClasses = useQuery({
    queryKey: ['my-classes'],
    queryFn: () => teachersApi.myClasses(),
  });

  const classrooms = myClasses.data?.classrooms ?? [];
  const selected = classroomId || (classrooms[0] ? String(classrooms[0].id) : '');

  const students = useQuery({
    queryKey: ['teacher-students', selected],
    queryFn: () => studentsApi.list({ classroom: selected, status: 'ACTIVE', page_size: '200' }),
    enabled: Boolean(selected),
  });

  const teacher = myClasses.data?.teacher;
  const selectedClassroom = classrooms.find((c: any) => String(c.id) === selected);

  if (myClasses.isLoading) {
    return <div className="page muted">جاري التحميل...</div>;
  }

  if (!teacher) {
    return (
      <div className="page">
        <h2>فصلي</h2>
        <p className="muted">لا يوجد ملف معلم مرتبط بهذا الحساب.</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>إدارة فصلي</h2>
          <p className="muted">
            {teacher.full_name} · {teacher.specialization || 'معلم'}
          </p>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <Link className="btn btn-primary" to={`/attendance?classroom=${selected}`}>
            تسجيل الحضور
          </Link>
        </div>
      </header>

      <div className="toolbar">
        <select value={selected} onChange={(e) => setClassroomId(e.target.value)}>
          {classrooms.map((c: any) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.student_count} طالب)
            </option>
          ))}
        </select>
      </div>

      {selectedClassroom && (
        <section className="stats-grid">
          <article className="stat-tile">
            <span>الفصل</span>
            <strong>{selectedClassroom.name}</strong>
          </article>
          <article className="stat-tile">
            <span>الطلاب</span>
            <strong>{selectedClassroom.student_count}</strong>
          </article>
          <article className="stat-tile">
            <span>المواد</span>
            <strong>{selectedClassroom.subjects?.length ?? 0}</strong>
          </article>
        </section>
      )}

      <section className="panel">
        <h3>موادي في هذا الفصل</h3>
        <ul className="feature-list">
          {(selectedClassroom?.subjects ?? []).map((s: any) => (
            <li key={s.id}>{s.name}</li>
          ))}
        </ul>
      </section>

      <div className="panel table-wrap">
        <h3>طلاب الفصل</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>الرمز</th>
              <th>الاسم</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(students.data?.results ?? []).map((s) => (
              <tr key={s.id}>
                <td>{s.student_code}</td>
                <td>{s.full_name}</td>
                <td>
                  <Link to={`/students/${s.id}`}>الملف</Link>
                </td>
              </tr>
            ))}
            {(students.data?.results ?? []).length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
                  لا يوجد طلاب في هذا الفصل.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
