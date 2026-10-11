import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { classesApi, studentsApi, transportApi, type Student } from '../api/resources';
import { PaginationBar } from '../components/PaginationBar';
import { useAuth } from '../context/AuthContext';

const PAGE_SIZE = 20;

const emptyForm = {
  student_code: '',
  first_name: '',
  father_name: '',
  last_name: '',
  gender: 'MALE',
  phone: '',
  address: '',
  status: 'ACTIVE',
  classroom: '',
  notes: '',
  assign_transport: false,
  bus: '',
  route: '',
  pickup_location: 'قرب المنزل',
  dropoff_location: 'المدرسة',
  monthly_fee: '25',
  transport_status: 'ACTIVE',
};

export function StudentsPage() {
  const { schoolContext } = useAuth();
  const canManage = (schoolContext?.permissions ?? []).includes('students.manage');
  const canManageTransport = (schoolContext?.permissions ?? []).includes('transport.manage');
  const hasTransport = (schoolContext?.features ?? []).includes('transport');
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [classroomFilter, setClassroomFilter] = useState('');
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['students', search, status, classroomFilter, page],
    queryFn: () =>
      studentsApi.list({
        page: String(page),
        page_size: String(PAGE_SIZE),
        ...(search ? { search } : {}),
        ...(status ? { status } : {}),
        ...(classroomFilter ? { classroom: classroomFilter } : {}),
      }),
  });

  const { data: classrooms } = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms({ page_size: '200' }),
  });

  const buses = useQuery({
    queryKey: ['buses'],
    queryFn: () => transportApi.listBuses(),
    enabled: hasTransport && canManageTransport,
  });
  const routes = useQuery({
    queryKey: ['routes'],
    queryFn: () => transportApi.listRoutes(),
    enabled: hasTransport && canManageTransport,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const {
        assign_transport,
        bus,
        route,
        pickup_location,
        dropoff_location,
        monthly_fee,
        transport_status,
        ...studentFields
      } = form;
      const payload = {
        ...studentFields,
        classroom: form.classroom ? Number(form.classroom) : null,
      } as Partial<Student>;
      const student = editingId
        ? await studentsApi.update(editingId, payload)
        : await studentsApi.create(payload);

      if (!editingId && assign_transport && canManageTransport && bus && route) {
        await transportApi.createAssignment({
          student: student.id,
          bus: Number(bus),
          route: Number(route),
          pickup_location,
          dropoff_location,
          monthly_fee,
          status: transport_status,
          notes: '',
        });
      }
      return student;
    },
    onSuccess: async () => {
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      setError('');
      await qc.invalidateQueries({ queryKey: ['students'] });
      await qc.invalidateQueries({ queryKey: ['transport-assignments'] });
    },
    onError: () => setError('تعذر حفظ الطالب. تحقق من الرمز والبيانات.'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => studentsApi.remove(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['students'] });
    },
  });

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(s: Student) {
    setEditingId(s.id);
    setForm({
      ...emptyForm,
      student_code: s.student_code,
      first_name: s.first_name,
      father_name: s.father_name || '',
      last_name: s.last_name,
      gender: s.gender || 'MALE',
      phone: s.phone || '',
      address: s.address || '',
      status: s.status,
      classroom: s.classroom ? String(s.classroom) : '',
      notes: s.notes || '',
      assign_transport: false,
    });
    setShowForm(true);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>الطلاب</h2>
          <p className="muted">إضافة · تعديل · حذف</p>
        </div>
        {canManage && (
          <button type="button" className="btn btn-primary" onClick={openCreate}>
            إضافة طالب
          </button>
        )}
      </header>

      <div className="toolbar">
        <input
          placeholder="بحث بالاسم أو الرمز..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">كل الحالات</option>
          <option value="ACTIVE">نشط</option>
          <option value="INACTIVE">غير نشط</option>
          <option value="GRADUATED">متخرج</option>
          <option value="TRANSFERRED">منقول</option>
        </select>
        <select
          value={classroomFilter}
          onChange={(e) => {
            setClassroomFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">كل الفصول</option>
          {(classrooms?.results ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {showForm && canManage && (
        <form className="panel form-grid" onSubmit={onSubmit}>
          <h3>{editingId ? 'تعديل طالب' : 'طالب جديد'}</h3>
          {error && <div className="alert error">{error}</div>}
          <label>
            رمز الطالب *
            <input
              required
              value={form.student_code}
              onChange={(e) => setForm({ ...form, student_code: e.target.value })}
            />
          </label>
          <label>
            الاسم الأول *
            <input
              required
              value={form.first_name}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
            />
          </label>
          <label>
            اسم الأب
            <input
              value={form.father_name}
              onChange={(e) => setForm({ ...form, father_name: e.target.value })}
            />
          </label>
          <label>
            اسم العائلة *
            <input
              required
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </label>
          <label>
            الجنس
            <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}>
              <option value="MALE">ذكر</option>
              <option value="FEMALE">أنثى</option>
            </select>
          </label>
          <label>
            الفصل
            <select
              value={form.classroom}
              onChange={(e) => setForm({ ...form, classroom: e.target.value })}
            >
              <option value="">— بدون فصل —</option>
              {(classrooms?.results ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            الحالة
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="ACTIVE">نشط</option>
              <option value="INACTIVE">غير نشط</option>
              <option value="GRADUATED">متخرج</option>
              <option value="TRANSFERRED">منقول</option>
            </select>
          </label>
          <label>
            الهاتف
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          <label className="full">
            العنوان
            <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </label>
          <label className="full">
            ملاحظات
            <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </label>

          {!editingId && hasTransport && canManageTransport && (
            <>
              <label className="full">
                ربط بالنقل عند الإضافة
                <select
                  value={form.assign_transport ? '1' : '0'}
                  onChange={(e) =>
                    setForm({ ...form, assign_transport: e.target.value === '1' })
                  }
                >
                  <option value="0">لا</option>
                  <option value="1">نعم</option>
                </select>
              </label>
              {form.assign_transport && (
                <>
                  <label>
                    الحافلة *
                    <select
                      required
                      value={form.bus}
                      onChange={(e) => setForm({ ...form, bus: e.target.value })}
                    >
                      <option value="">اختر الحافلة</option>
                      {(buses.data?.results ?? []).map((b: { id: number; bus_number: string }) => (
                        <option key={b.id} value={b.id}>
                          {b.bus_number}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    المسار *
                    <select
                      required
                      value={form.route}
                      onChange={(e) => setForm({ ...form, route: e.target.value })}
                    >
                      <option value="">اختر المسار</option>
                      {(routes.data?.results ?? []).map((r: { id: number; name: string }) => (
                        <option key={r.id} value={r.id}>
                          {r.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    نقطة الاصطحاب
                    <input
                      value={form.pickup_location}
                      onChange={(e) => setForm({ ...form, pickup_location: e.target.value })}
                    />
                  </label>
                  <label>
                    نقطة التوصيل
                    <input
                      value={form.dropoff_location}
                      onChange={(e) => setForm({ ...form, dropoff_location: e.target.value })}
                    />
                  </label>
                  <label>
                    الرسوم الشهرية
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={form.monthly_fee}
                      onChange={(e) => setForm({ ...form, monthly_fee: e.target.value })}
                    />
                  </label>
                  <label>
                    حالة النقل
                    <select
                      value={form.transport_status}
                      onChange={(e) => setForm({ ...form, transport_status: e.target.value })}
                    >
                      <option value="ACTIVE">نشط</option>
                      <option value="INACTIVE">غير نشط</option>
                    </select>
                  </label>
                </>
              )}
            </>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saveMutation.isPending}>
              حفظ
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
              }}
            >
              إلغاء
            </button>
          </div>
        </form>
      )}

      <div className="panel table-wrap">
        {isLoading ? (
          <p className="muted">جاري التحميل...</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>الرمز</th>
                <th>الاسم</th>
                <th>الفصل</th>
                <th>الحالة</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((s) => (
                <tr key={s.id}>
                  <td>{s.student_code}</td>
                  <td>{s.full_name}</td>
                  <td>{s.classroom_name || '—'}</td>
                  <td>{s.status}</td>
                  <td className="actions-cell">
                    <Link className="link-btn" to={`/students/${s.id}`}>
                      عرض
                    </Link>
                    {canManage && (
                      <>
                        <button type="button" className="link-btn" onClick={() => openEdit(s)}>
                          تعديل
                        </button>
                        <button
                          type="button"
                          className="link-btn danger"
                          onClick={() => {
                            if (confirm('حذف هذا الطالب؟')) deleteMutation.mutate(s.id);
                          }}
                        >
                          حذف
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {(data?.results ?? []).length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">
                    لا يوجد طلاب.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <PaginationBar
          page={page}
          pageSize={PAGE_SIZE}
          count={data?.count ?? 0}
          onPageChange={setPage}
          label="طالب"
        />
      </div>
    </div>
  );
}
