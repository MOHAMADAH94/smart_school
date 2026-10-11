import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { classesApi, parentsApi, studentsApi, transportApi } from '../api/resources';
import { useAuth } from '../context/AuthContext';

type TabKey = 'info' | 'parents' | 'attendance' | 'grades' | 'transport' | 'payments' | 'notes';

export function StudentDetailPage() {
  const { id } = useParams();
  const studentId = Number(id);
  const { schoolContext } = useAuth();
  const features = new Set(schoolContext?.features ?? []);
  const canManage = (schoolContext?.permissions ?? []).includes('students.manage');
  const canManageParents = (schoolContext?.permissions ?? []).includes('parents.manage');
  const canManageTransport = (schoolContext?.permissions ?? []).includes('transport.manage');
  const canManageFinance = (schoolContext?.permissions ?? []).includes('finance.manage');
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>('info');
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({});
  const [parentLinkForm, setParentLinkForm] = useState({
    parent: '',
    relationship: 'FATHER',
    is_primary: true,
  });
  const [transportForm, setTransportForm] = useState({
    bus: '',
    route: '',
    pickup_location: 'قرب المنزل',
    dropoff_location: 'المدرسة',
    monthly_fee: '25',
    status: 'ACTIVE',
    notes: '',
  });
  const [paymentForm, setPaymentForm] = useState({
    fee: '',
    amount: '',
    payment_date: new Date().toISOString().slice(0, 10),
    method: 'CASH',
    reference: '',
  });
  const [paymentError, setPaymentError] = useState('');

  const profile = useQuery({
    queryKey: ['student-profile', studentId],
    queryFn: () => studentsApi.profile(studentId),
    enabled: Boolean(studentId),
  });
  const classrooms = useQuery({
    queryKey: ['classrooms'],
    queryFn: () => classesApi.listClassrooms(),
  });
  const parentsList = useQuery({
    queryKey: ['parents'],
    queryFn: () => parentsApi.list(),
    enabled: canManageParents && features.has('parents'),
  });
  const buses = useQuery({
    queryKey: ['buses'],
    queryFn: () => transportApi.listBuses(),
    enabled: features.has('transport'),
  });
  const routes = useQuery({
    queryKey: ['routes'],
    queryFn: () => transportApi.listRoutes(),
    enabled: features.has('transport'),
  });

  const student = profile.data?.student;
  const transport = profile.data?.transport;

  useEffect(() => {
    if (!transport) return;
    setTransportForm({
      bus: String(transport.bus ?? ''),
      route: String(transport.route ?? ''),
      pickup_location: transport.pickup_location || 'قرب المنزل',
      dropoff_location: transport.dropoff_location || 'المدرسة',
      monthly_fee: String(transport.monthly_fee ?? '25'),
      status: transport.status || 'ACTIVE',
      notes: transport.notes || '',
    });
  }, [transport]);

  const saveInfo = useMutation({
    mutationFn: () =>
      studentsApi.update(studentId, {
        ...form,
        classroom: form.classroom ? Number(form.classroom) : null,
      } as any),
    onSuccess: async () => {
      setEditMode(false);
      await qc.invalidateQueries({ queryKey: ['student-profile', studentId] });
      await qc.invalidateQueries({ queryKey: ['students'] });
    },
  });

  const saveTransport = useMutation({
    mutationFn: async () => {
      const payload = {
        student: studentId,
        bus: Number(transportForm.bus),
        route: Number(transportForm.route),
        pickup_location: transportForm.pickup_location,
        dropoff_location: transportForm.dropoff_location,
        monthly_fee: transportForm.monthly_fee,
        status: transportForm.status,
        notes: transportForm.notes,
      };
      if (transport?.id) {
        return transportApi.updateAssignment(transport.id, payload);
      }
      return transportApi.createAssignment(payload);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['student-profile', studentId] });
    },
  });

  const linkParent = useMutation({
    mutationFn: () =>
      parentsApi.linkStudent({
        student: studentId,
        parent: Number(parentLinkForm.parent),
        relationship: parentLinkForm.relationship,
        is_primary: parentLinkForm.is_primary,
      }),
    onSuccess: async () => {
      setParentLinkForm({ parent: '', relationship: 'FATHER', is_primary: true });
      await qc.invalidateQueries({ queryKey: ['student-profile', studentId] });
      await qc.invalidateQueries({ queryKey: ['student-parent-links'] });
    },
  });

  const unlinkParent = useMutation({
    mutationFn: (linkId: number) => parentsApi.unlinkStudent(linkId),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['student-profile', studentId] });
      await qc.invalidateQueries({ queryKey: ['student-parent-links'] });
    },
  });

  const createPayment = useMutation({
    mutationFn: async () =>
      api.post('/finance/payments/', {
        student: studentId,
        fee: Number(paymentForm.fee),
        amount: paymentForm.amount,
        payment_date: paymentForm.payment_date,
        method: paymentForm.method,
        reference: paymentForm.reference,
      }),
    onSuccess: async () => {
      setPaymentForm({
        fee: '',
        amount: '',
        payment_date: new Date().toISOString().slice(0, 10),
        method: 'CASH',
        reference: '',
      });
      setPaymentError('');
      await qc.invalidateQueries({ queryKey: ['student-profile', studentId] });
      await qc.invalidateQueries({ queryKey: ['fees'] });
      await qc.invalidateQueries({ queryKey: ['payments'] });
      await qc.invalidateQueries({ queryKey: ['finance-summary'] });
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg = data?.detail || data?.fee || data?.amount || 'تعذر تسجيل الدفعة.';
      setPaymentError(Array.isArray(msg) ? String(msg[0]) : String(msg));
    },
  });

  function startEdit() {
    if (!student) return;
    setForm({
      student_code: student.student_code,
      first_name: student.first_name,
      father_name: student.father_name || '',
      last_name: student.last_name,
      gender: student.gender || 'MALE',
      phone: student.phone || '',
      address: student.address || '',
      status: student.status,
      classroom: student.classroom ? String(student.classroom) : '',
      notes: student.notes || '',
    });
    setEditMode(true);
  }

  function onSaveInfo(e: FormEvent) {
    e.preventDefault();
    saveInfo.mutate();
  }

  function onSaveTransport(e: FormEvent) {
    e.preventDefault();
    saveTransport.mutate();
  }

  if (profile.isLoading) return <div className="page muted">جاري التحميل...</div>;
  if (!student) return <div className="page">الطالب غير موجود.</div>;

  const tabs: { key: TabKey; label: string; show: boolean }[] = [
    { key: 'info', label: 'المعلومات', show: true },
    { key: 'parents', label: 'أولياء الأمور', show: features.has('parents') },
    { key: 'attendance', label: 'الحضور', show: features.has('attendance') },
    { key: 'grades', label: 'الدرجات', show: features.has('grades') },
    { key: 'transport', label: 'النقل', show: features.has('transport') },
    { key: 'payments', label: 'المدفوعات', show: features.has('payments') || features.has('fees') },
    { key: 'notes', label: 'ملاحظات', show: true },
  ];

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <Link to="/students" className="muted">
            ← الطلاب
          </Link>
          <h2>{student.full_name}</h2>
          <p className="muted">
            {student.student_code} · {student.classroom_name || 'بدون فصل'}
          </p>
        </div>
        {canManage && tab === 'info' && !editMode && (
          <button type="button" className="btn btn-primary" onClick={startEdit}>
            تعديل البيانات
          </button>
        )}
      </header>

      <div className="tabs">
        {tabs
          .filter((t) => t.show)
          .map((t) => (
            <button
              key={t.key}
              type="button"
              className={tab === t.key ? 'tab active' : 'tab'}
              onClick={() => {
                setTab(t.key);
                setEditMode(false);
              }}
            >
              {t.label}
            </button>
          ))}
      </div>

      {tab === 'info' && (
        <>
          {editMode ? (
            <form className="panel form-grid" onSubmit={onSaveInfo}>
              <label>
                الرمز
                <input
                  required
                  value={form.student_code}
                  onChange={(e) => setForm({ ...form, student_code: e.target.value })}
                />
              </label>
              <label>
                الاسم الأول
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
                العائلة
                <input
                  required
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                />
              </label>
              <label>
                الفصل
                <select
                  value={form.classroom}
                  onChange={(e) => setForm({ ...form, classroom: e.target.value })}
                >
                  <option value="">بدون فصل</option>
                  {(classrooms.data?.results ?? []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                الحالة
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
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
                <input
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                />
              </label>
              <div className="form-actions">
                <button className="btn btn-primary" type="submit">
                  حفظ
                </button>
                <button className="btn btn-ghost" type="button" onClick={() => setEditMode(false)}>
                  إلغاء
                </button>
              </div>
            </form>
          ) : (
            <section className="panel detail-grid">
              <div>
                <span className="muted">الاسم الأول</span>
                <strong>{student.first_name}</strong>
              </div>
              <div>
                <span className="muted">اسم الأب</span>
                <strong>{student.father_name || '—'}</strong>
              </div>
              <div>
                <span className="muted">العائلة</span>
                <strong>{student.last_name}</strong>
              </div>
              <div>
                <span className="muted">الفصل</span>
                <strong>{student.classroom_name || '—'}</strong>
              </div>
              <div>
                <span className="muted">الجنس</span>
                <strong>{student.gender || '—'}</strong>
              </div>
              <div>
                <span className="muted">الحالة</span>
                <strong>{student.status}</strong>
              </div>
              <div>
                <span className="muted">الهاتف</span>
                <strong>{student.phone || '—'}</strong>
              </div>
              <div className="full">
                <span className="muted">العنوان</span>
                <strong>{student.address || '—'}</strong>
              </div>
            </section>
          )}
        </>
      )}

      {tab === 'parents' && (
        <div className="panel">
          {canManageParents && (
            <form
              className="form-grid"
              onSubmit={(e) => {
                e.preventDefault();
                linkParent.mutate();
              }}
            >
              <h3>ربط ولي أمر</h3>
              <label>
                ولي الأمر *
                <select
                  required
                  value={parentLinkForm.parent}
                  onChange={(e) => setParentLinkForm({ ...parentLinkForm, parent: e.target.value })}
                >
                  <option value="">اختر ولي الأمر</option>
                  {(parentsList.data?.results ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                الصلة *
                <select
                  value={parentLinkForm.relationship}
                  onChange={(e) =>
                    setParentLinkForm({ ...parentLinkForm, relationship: e.target.value })
                  }
                >
                  <option value="FATHER">أب</option>
                  <option value="MOTHER">أم</option>
                  <option value="GUARDIAN">وصي</option>
                  <option value="OTHER">أخرى</option>
                </select>
              </label>
              <label>
                أساسي؟
                <select
                  value={parentLinkForm.is_primary ? '1' : '0'}
                  onChange={(e) =>
                    setParentLinkForm({
                      ...parentLinkForm,
                      is_primary: e.target.value === '1',
                    })
                  }
                >
                  <option value="1">نعم</option>
                  <option value="0">لا</option>
                </select>
              </label>
              <div className="form-actions">
                <button type="submit" className="btn btn-primary" disabled={linkParent.isPending}>
                  ربط
                </button>
              </div>
            </form>
          )}
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>الاسم</th>
                  <th>الصلة</th>
                  <th>الهاتف</th>
                  <th>البريد</th>
                  {canManageParents && <th>إجراءات</th>}
                </tr>
              </thead>
              <tbody>
                {(profile.data?.parents ?? []).map((p: any) => (
                  <tr key={`${p.link_id || p.id}-${p.relationship}`}>
                    <td>{p.name}</td>
                    <td>{p.relationship}</td>
                    <td>{p.phone || '—'}</td>
                    <td>{p.email || '—'}</td>
                    {canManageParents && (
                      <td>
                        {p.link_id ? (
                          <button
                            type="button"
                            className="link-btn danger"
                            onClick={() => {
                              if (confirm('إلغاء ربط ولي الأمر؟')) unlinkParent.mutate(p.link_id);
                            }}
                          >
                            إلغاء الربط
                          </button>
                        ) : (
                          '—'
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {(profile.data?.parents ?? []).length === 0 && (
                  <tr>
                    <td colSpan={canManageParents ? 5 : 4} className="muted">
                      لا يوجد أولياء أمور مرتبطون.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'attendance' && (
        <div className="panel table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>التاريخ</th>
                <th>الحالة</th>
                <th>ملاحظات</th>
              </tr>
            </thead>
            <tbody>
              {(profile.data?.attendance ?? []).map((a: any) => (
                <tr key={a.id}>
                  <td>{a.date}</td>
                  <td>{a.status}</td>
                  <td>{a.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'grades' && (
        <div className="panel table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>التقييم</th>
                <th>المادة</th>
                <th>الفصل الدراسي</th>
                <th>الدرجة</th>
              </tr>
            </thead>
            <tbody>
              {(profile.data?.grades ?? []).map((g: any) => (
                <tr key={g.id}>
                  <td>{g.assessment_name}</td>
                  <td>{g.subject_name}</td>
                  <td>{g.term_name}</td>
                  <td>
                    {g.score} / {g.max_score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'transport' && (
        <div className="split-grid">
          <section className="panel">
            <h3>النقل الحالي</h3>
            {transport ? (
              <div className="detail-grid">
                <div>
                  <span className="muted">الحافلة</span>
                  <strong>{transport.bus_number}</strong>
                </div>
                <div>
                  <span className="muted">المسار</span>
                  <strong>{transport.route_name}</strong>
                </div>
                <div>
                  <span className="muted">الاستلام</span>
                  <strong>{transport.pickup_location || '—'}</strong>
                </div>
                <div>
                  <span className="muted">التوصيل</span>
                  <strong>{transport.dropoff_location || '—'}</strong>
                </div>
                <div>
                  <span className="muted">الرسوم الشهرية</span>
                  <strong>{transport.monthly_fee}</strong>
                </div>
                <div>
                  <span className="muted">الحالة</span>
                  <strong>{transport.status}</strong>
                </div>
              </div>
            ) : (
              <p className="muted">لا يوجد تعيين نقل لهذا الطالب.</p>
            )}
          </section>

          {canManageTransport && (
            <form className="panel form-grid" onSubmit={onSaveTransport}>
              <h3>{transport ? 'تعديل النقل' : 'تعيين وسيلة نقل'}</h3>
              <label>
                الحافلة *
                <select
                  required
                  value={transportForm.bus || (transport?.bus ? String(transport.bus) : '')}
                  onChange={(e) => setTransportForm({ ...transportForm, bus: e.target.value })}
                >
                  <option value="">اختر</option>
                  {(buses.data?.results ?? []).map((b: any) => (
                    <option key={b.id} value={b.id}>
                      {b.bus_number} ({b.vehicle_type})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                المسار *
                <select
                  required
                  value={transportForm.route || (transport?.route ? String(transport.route) : '')}
                  onChange={(e) => setTransportForm({ ...transportForm, route: e.target.value })}
                >
                  <option value="">اختر</option>
                  {(routes.data?.results ?? []).map((r: any) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                موقع الاستلام
                <input
                  value={transportForm.pickup_location}
                  onChange={(e) =>
                    setTransportForm({ ...transportForm, pickup_location: e.target.value })
                  }
                />
              </label>
              <label>
                موقع التوصيل
                <input
                  value={transportForm.dropoff_location}
                  onChange={(e) =>
                    setTransportForm({ ...transportForm, dropoff_location: e.target.value })
                  }
                />
              </label>
              <label>
                الرسوم الشهرية
                <input
                  value={transportForm.monthly_fee}
                  onChange={(e) => setTransportForm({ ...transportForm, monthly_fee: e.target.value })}
                />
              </label>
              <label>
                الحالة
                <select
                  value={transportForm.status}
                  onChange={(e) => setTransportForm({ ...transportForm, status: e.target.value })}
                >
                  <option value="ACTIVE">نشط</option>
                  <option value="INACTIVE">غير نشط</option>
                  <option value="SUSPENDED">موقوف</option>
                </select>
              </label>
              <div className="form-actions">
                <button className="btn btn-primary" type="submit" disabled={saveTransport.isPending}>
                  حفظ النقل
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {tab === 'payments' && (
        <div className="split-grid">
          <div className="panel table-wrap">
            <h3>الرسوم</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>العنوان</th>
                  <th>المبلغ</th>
                  <th>المدفوع</th>
                  <th>المتبقي</th>
                </tr>
              </thead>
              <tbody>
                {(profile.data?.fees ?? []).map((f: any) => (
                  <tr key={f.id}>
                    <td>{f.title}</td>
                    <td>{f.amount}</td>
                    <td>{f.paid_amount}</td>
                    <td>{f.remaining_amount}</td>
                  </tr>
                ))}
                {(profile.data?.fees ?? []).length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                      لا توجد رسوم. أضفها من صفحة المالية.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="panel table-wrap">
            <h3>المدفوعات</h3>
            {canManageFinance && features.has('payments') && (
              <form
                className="form-grid"
                style={{ marginBottom: '1rem' }}
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  createPayment.mutate();
                }}
              >
                {paymentError && <div className="alert error full">{paymentError}</div>}
                <label>
                  الرسوم *
                  <select
                    required
                    value={paymentForm.fee}
                    onChange={(e) => {
                      const fee = (profile.data?.fees ?? []).find(
                        (f: any) => String(f.id) === e.target.value,
                      );
                      setPaymentForm({
                        ...paymentForm,
                        fee: e.target.value,
                        amount:
                          fee?.remaining_amount != null && Number(fee.remaining_amount) > 0
                            ? String(fee.remaining_amount)
                            : paymentForm.amount,
                      });
                    }}
                  >
                    <option value="">اختر</option>
                    {(profile.data?.fees ?? []).map((f: any) => (
                      <option key={f.id} value={f.id}>
                        {f.title} — متبقي {f.remaining_amount}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  المبلغ *
                  <input
                    required
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                  />
                </label>
                <label>
                  التاريخ *
                  <input
                    required
                    type="date"
                    value={paymentForm.payment_date}
                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                  />
                </label>
                <label>
                  الطريقة
                  <select
                    value={paymentForm.method}
                    onChange={(e) => setPaymentForm({ ...paymentForm, method: e.target.value })}
                  >
                    <option value="CASH">نقداً</option>
                    <option value="CARD">بطاقة</option>
                    <option value="BANK">تحويل بنكي</option>
                    <option value="OTHER">أخرى</option>
                  </select>
                </label>
                <div className="form-actions full">
                  <button className="btn btn-primary" type="submit" disabled={createPayment.isPending}>
                    تسجيل دفعة
                  </button>
                </div>
              </form>
            )}
            <table className="data-table">
              <thead>
                <tr>
                  <th>التاريخ</th>
                  <th>المبلغ</th>
                  <th>الطريقة</th>
                </tr>
              </thead>
              <tbody>
                {(profile.data?.payments ?? []).map((p: any) => (
                  <tr key={p.id}>
                    <td>{p.payment_date}</td>
                    <td>{p.amount}</td>
                    <td>{p.method}</td>
                  </tr>
                ))}
                {(profile.data?.payments ?? []).length === 0 && (
                  <tr>
                    <td colSpan={3} className="muted">
                      لا توجد مدفوعات بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'notes' && (
        <section className="panel">
          <h3>ملاحظات</h3>
          <p>{student.notes || 'لا توجد ملاحظات.'}</p>
        </section>
      )}
    </div>
  );
}
