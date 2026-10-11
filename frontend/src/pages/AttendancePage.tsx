import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { classesApi, studentsApi, teachersApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';

type Status = 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED';

export function AttendancePage() {
  const { schoolContext } = useAuth();
  const isTeacher = schoolContext?.membership?.role === 'TEACHER';
  const qc = useQueryClient();
  const [searchParams] = useSearchParams();
  const [classroomId, setClassroomId] = useState(searchParams.get('classroom') || '');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [marks, setMarks] = useState<Record<number, Status>>({});

  useEffect(() => {
    const fromQuery = searchParams.get('classroom');
    if (fromQuery) setClassroomId(fromQuery);
  }, [searchParams]);

  const classrooms = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms(),
    enabled: !isTeacher,
  });
  const myClasses = useQuery({
    queryKey: ['my-classes'],
    queryFn: () => teachersApi.myClasses(),
    enabled: isTeacher,
  });

  const classroomOptions = isTeacher
    ? (myClasses.data?.classrooms ?? []).map((c: { id: number; name: string }) => ({
        id: c.id,
        name: c.name,
      }))
    : (classrooms.data?.results ?? []);

  const students = useQuery({
    queryKey: ['attendance-students', classroomId],
    queryFn: () => studentsApi.list({ classroom: classroomId, status: 'ACTIVE', page_size: '200' }),
    enabled: Boolean(classroomId),
  });

  const studentList = students.data?.results ?? [];

  useEffect(() => {
    if (!studentList.length) return;
    setMarks((prev) => {
      const next = { ...prev };
      for (const s of studentList) {
        if (!next[s.id]) next[s.id] = 'PRESENT';
      }
      return next;
    });
  }, [studentList]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const records = Object.entries(marks).map(([student_id, status]) => ({
        student_id: Number(student_id),
        status,
      }));
      await api.post('/attendance/bulk/', {
        classroom_id: Number(classroomId),
        date,
        default_status: 'PRESENT',
        records,
      });
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['dashboard'] });
      alert('تم حفظ الحضور');
    },
  });

  function markAllPresent() {
    const next: Record<number, Status> = {};
    for (const s of studentList) next[s.id] = 'PRESENT';
    setMarks(next);
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>الحضور</h2>
          <p className="muted">اختر الفصل، علّم الكل حاضر، ثم عدّل الغياب</p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!classroomId || saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          حفظ
        </button>
      </header>

      <div className="toolbar">
        <select value={classroomId} onChange={(e) => setClassroomId(e.target.value)}>
          <option value="">اختر الفصل</option>
          {(classroomOptions).map((c: any) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button type="button" className="btn btn-ghost" onClick={markAllPresent} disabled={!classroomId}>
          تعليم الكل حاضر
        </button>
      </div>

      <div className="attendance-list">
        {studentList.map((s) => (
          <div key={s.id} className="attendance-row">
            <div>
              <strong>{s.full_name}</strong>
              <div className="muted">{s.student_code}</div>
            </div>
            <div className="status-pills">
              {(
                [
                  ['PRESENT', 'حاضر', 'active-present'],
                  ['ABSENT', 'غائب', 'active-absent'],
                  ['LATE', 'متأخر', 'active-late'],
                  ['EXCUSED', 'بعذر', 'active-excused'],
                ] as const
              ).map(([value, label, cls]) => (
                <button
                  key={value}
                  type="button"
                  className={marks[s.id] === value ? cls : ''}
                  onClick={() => setMarks({ ...marks, [s.id]: value })}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
        {classroomId && studentList.length === 0 && (
          <p className="muted">لا يوجد طلاب في هذا الفصل.</p>
        )}
      </div>
    </div>
  );
}
