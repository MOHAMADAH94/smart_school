import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { studentsApi, transportApi } from '../api/resources';

interface Bus {
  id: number;
  bus_number: string;
  vehicle_type: string;
  capacity: number;
  driver_name?: string;
  phone: string;
  is_active: boolean;
  student_count: number;
}

interface RouteItem {
  id: number;
  name: string;
  bus_number?: string;
  driver_name?: string;
  driver_phone?: string;
  student_count: number;
  start_location: string;
  end_location: string;
  stops: string;
}

export function TransportPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'assign' | 'buses' | 'routes' | 'drivers'>('assign');
  const [busForm, setBusForm] = useState({
    bus_number: '',
    vehicle_type: 'BUS',
    capacity: '20',
    phone: '',
  });
  const [routeForm, setRouteForm] = useState({
    name: '',
    start_location: '',
    end_location: '',
    stops: '',
    bus: '',
  });
  const [driverForm, setDriverForm] = useState({ name: '', phone: '', license_number: '' });
  const [assignForm, setAssignForm] = useState({
    student: '',
    bus: '',
    route: '',
    pickup_location: 'قرب المنزل',
    dropoff_location: 'المدرسة',
    monthly_fee: '25',
    status: 'ACTIVE',
  });
  const [assignError, setAssignError] = useState('');

  const buses = useQuery({
    queryKey: ['buses'],
    queryFn: async () => (await api.get('/transport/buses/')).data,
  });
  const routes = useQuery({
    queryKey: ['routes'],
    queryFn: async () => (await api.get('/transport/routes/')).data,
  });
  const drivers = useQuery({
    queryKey: ['drivers'],
    queryFn: async () => (await api.get('/transport/drivers/')).data,
  });
  const assignments = useQuery({
    queryKey: ['transport-assignments'],
    queryFn: () => transportApi.listAssignments(),
  });
  const students = useQuery({
    queryKey: ['students-transport'],
    queryFn: () => studentsApi.list({ status: 'ACTIVE' }),
  });

  const busResults: Bus[] = buses.data?.results ?? buses.data ?? [];
  const routeResults: RouteItem[] = routes.data?.results ?? routes.data ?? [];
  const driverResults = drivers.data?.results ?? drivers.data ?? [];
  const assignmentRows = assignments.data?.results ?? [];

  const createBus = useMutation({
    mutationFn: async () =>
      api.post('/transport/buses/', {
        ...busForm,
        capacity: Number(busForm.capacity),
      }),
    onSuccess: async () => {
      setBusForm({ bus_number: '', vehicle_type: 'BUS', capacity: '20', phone: '' });
      await qc.invalidateQueries({ queryKey: ['buses'] });
    },
  });

  const createRoute = useMutation({
    mutationFn: async () =>
      api.post('/transport/routes/', {
        ...routeForm,
        bus: routeForm.bus ? Number(routeForm.bus) : null,
      }),
    onSuccess: async () => {
      setRouteForm({ name: '', start_location: '', end_location: '', stops: '', bus: '' });
      await qc.invalidateQueries({ queryKey: ['routes'] });
    },
  });

  const createDriver = useMutation({
    mutationFn: async () => api.post('/transport/drivers/', driverForm),
    onSuccess: async () => {
      setDriverForm({ name: '', phone: '', license_number: '' });
      await qc.invalidateQueries({ queryKey: ['drivers'] });
    },
  });

  const saveAssignment = useMutation({
    mutationFn: async () => {
      const existing = assignmentRows.find((a) => String(a.student) === assignForm.student);
      const payload = {
        student: Number(assignForm.student),
        bus: Number(assignForm.bus),
        route: Number(assignForm.route),
        pickup_location: assignForm.pickup_location,
        dropoff_location: assignForm.dropoff_location,
        monthly_fee: assignForm.monthly_fee,
        status: assignForm.status,
      };
      if (existing?.id) {
        return transportApi.updateAssignment(existing.id, payload);
      }
      return transportApi.createAssignment(payload);
    },
    onSuccess: async () => {
      setAssignError('');
      setAssignForm({
        student: '',
        bus: '',
        route: '',
        pickup_location: 'قرب المنزل',
        dropoff_location: 'المدرسة',
        monthly_fee: '25',
        status: 'ACTIVE',
      });
      await qc.invalidateQueries({ queryKey: ['transport-assignments'] });
      await qc.invalidateQueries({ queryKey: ['buses'] });
      await qc.invalidateQueries({ queryKey: ['routes'] });
    },
    onError: () => setAssignError('تعذر تعيين النقل. تأكد من اختيار الطالب والحافلة والمسار.'),
  });

  const removeAssignment = useMutation({
    mutationFn: (id: number) => transportApi.removeAssignment(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['transport-assignments'] });
      await qc.invalidateQueries({ queryKey: ['buses'] });
    },
  });

  function submitBus(e: FormEvent) {
    e.preventDefault();
    createBus.mutate();
  }
  function submitRoute(e: FormEvent) {
    e.preventDefault();
    createRoute.mutate();
  }
  function submitDriver(e: FormEvent) {
    e.preventDefault();
    createDriver.mutate();
  }
  function submitAssign(e: FormEvent) {
    e.preventDefault();
    saveAssignment.mutate();
  }

  function loadStudentAssignment(studentId: string) {
    const existing = assignmentRows.find((a) => String(a.student) === studentId);
    setAssignForm({
      student: studentId,
      bus: existing ? String(existing.bus) : '',
      route: existing ? String(existing.route) : '',
      pickup_location: existing?.pickup_location || 'قرب المنزل',
      dropoff_location: existing?.dropoff_location || 'المدرسة',
      monthly_fee: existing ? String(existing.monthly_fee) : '25',
      status: existing?.status || 'ACTIVE',
    });
  }

  return (
    <div className="page">
      <header className="page-header">
        <h2>النقل المدرسي</h2>
        <p className="muted">تعيين باص لكل طالب · حافلات · مسارات · سائقون</p>
        <div className="tabs">
          <button
            type="button"
            className={tab === 'assign' ? 'tab active' : 'tab'}
            onClick={() => setTab('assign')}
          >
            تعيين الطلاب
          </button>
          <button
            type="button"
            className={tab === 'buses' ? 'tab active' : 'tab'}
            onClick={() => setTab('buses')}
          >
            الحافلات
          </button>
          <button
            type="button"
            className={tab === 'routes' ? 'tab active' : 'tab'}
            onClick={() => setTab('routes')}
          >
            المسارات
          </button>
          <button
            type="button"
            className={tab === 'drivers' ? 'tab active' : 'tab'}
            onClick={() => setTab('drivers')}
          >
            السائقون
          </button>
        </div>
      </header>

      {tab === 'assign' && (
        <>
          <form className="panel form-grid" onSubmit={submitAssign}>
            <h3>تعيين باص / مسار لطالب</h3>
            {assignError && <div className="alert error">{assignError}</div>}
            <label>
              الطالب *
              <select
                required
                value={assignForm.student}
                onChange={(e) => loadStudentAssignment(e.target.value)}
              >
                <option value="">اختر الطالب</option>
                {(students.data?.results ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.student_code})
                  </option>
                ))}
              </select>
            </label>
            <label>
              الحافلة *
              <select
                required
                value={assignForm.bus}
                onChange={(e) => setAssignForm({ ...assignForm, bus: e.target.value })}
              >
                <option value="">اختر الحافلة</option>
                {busResults.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.bus_number} — {b.vehicle_type} (سعة {b.capacity})
                  </option>
                ))}
              </select>
            </label>
            <label>
              المسار *
              <select
                required
                value={assignForm.route}
                onChange={(e) => setAssignForm({ ...assignForm, route: e.target.value })}
              >
                <option value="">اختر المسار</option>
                {routeResults.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} {r.bus_number ? `(${r.bus_number})` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label>
              الحالة
              <select
                value={assignForm.status}
                onChange={(e) => setAssignForm({ ...assignForm, status: e.target.value })}
              >
                <option value="ACTIVE">نشط</option>
                <option value="INACTIVE">غير نشط</option>
                <option value="SUSPENDED">موقوف</option>
              </select>
            </label>
            <label>
              موقع الاستلام
              <input
                value={assignForm.pickup_location}
                onChange={(e) => setAssignForm({ ...assignForm, pickup_location: e.target.value })}
              />
            </label>
            <label>
              موقع التوصيل
              <input
                value={assignForm.dropoff_location}
                onChange={(e) => setAssignForm({ ...assignForm, dropoff_location: e.target.value })}
              />
            </label>
            <label>
              الرسوم الشهرية
              <input
                value={assignForm.monthly_fee}
                onChange={(e) => setAssignForm({ ...assignForm, monthly_fee: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={saveAssignment.isPending}>
                حفظ التعيين
              </button>
            </div>
          </form>

          <div className="panel table-wrap">
            <h3>التعيينات الحالية</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>الطالب</th>
                  <th>الحافلة</th>
                  <th>المسار</th>
                  <th>الرسوم</th>
                  <th>الحالة</th>
                  <th>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {assignmentRows.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link to={`/students/${a.student}`}>{a.student_name || a.student}</Link>
                    </td>
                    <td>{a.bus_number}</td>
                    <td>{a.route_name}</td>
                    <td>{a.monthly_fee}</td>
                    <td>{a.status}</td>
                    <td className="actions-cell">
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => loadStudentAssignment(String(a.student))}
                      >
                        تعديل
                      </button>
                      <button
                        type="button"
                        className="link-btn danger"
                        onClick={() => {
                          if (confirm('إلغاء تعيين النقل؟')) removeAssignment.mutate(a.id);
                        }}
                      >
                        إلغاء
                      </button>
                    </td>
                  </tr>
                ))}
                {assignmentRows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      لا توجد تعيينات نقل بعد.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'buses' && (
        <>
          <form className="panel form-grid" onSubmit={submitBus}>
            <h3>إضافة مركبة</h3>
            <label>
              الرقم *
              <input
                required
                value={busForm.bus_number}
                onChange={(e) => setBusForm({ ...busForm, bus_number: e.target.value })}
                placeholder="#03"
              />
            </label>
            <label>
              النوع
              <select
                value={busForm.vehicle_type}
                onChange={(e) => setBusForm({ ...busForm, vehicle_type: e.target.value })}
              >
                <option value="BUS">حافلة</option>
                <option value="VAN">فان</option>
                <option value="MINIBUS">ميني باص</option>
                <option value="CAR">سيارة</option>
                <option value="OTHER">أخرى</option>
              </select>
            </label>
            <label>
              السعة
              <input
                value={busForm.capacity}
                onChange={(e) => setBusForm({ ...busForm, capacity: e.target.value })}
              />
            </label>
            <label>
              الهاتف
              <input
                value={busForm.phone}
                onChange={(e) => setBusForm({ ...busForm, phone: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit">
                حفظ
              </button>
            </div>
          </form>
          <div className="panel table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>الرقم</th>
                  <th>النوع</th>
                  <th>السعة</th>
                  <th>الطلاب</th>
                  <th>السائق</th>
                </tr>
              </thead>
              <tbody>
                {busResults.map((b) => (
                  <tr key={b.id}>
                    <td>{b.bus_number}</td>
                    <td>{b.vehicle_type}</td>
                    <td>{b.capacity}</td>
                    <td>{b.student_count}</td>
                    <td>{b.driver_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'routes' && (
        <>
          <form className="panel form-grid" onSubmit={submitRoute}>
            <h3>إضافة مسار</h3>
            <label>
              الاسم *
              <input
                required
                value={routeForm.name}
                onChange={(e) => setRouteForm({ ...routeForm, name: e.target.value })}
              />
            </label>
            <label>
              الحافلة
              <select
                value={routeForm.bus}
                onChange={(e) => setRouteForm({ ...routeForm, bus: e.target.value })}
              >
                <option value="">—</option>
                {busResults.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.bus_number}
                  </option>
                ))}
              </select>
            </label>
            <label>
              من
              <input
                value={routeForm.start_location}
                onChange={(e) => setRouteForm({ ...routeForm, start_location: e.target.value })}
              />
            </label>
            <label>
              إلى
              <input
                value={routeForm.end_location}
                onChange={(e) => setRouteForm({ ...routeForm, end_location: e.target.value })}
              />
            </label>
            <label className="full">
              المحطات
              <input
                value={routeForm.stops}
                onChange={(e) => setRouteForm({ ...routeForm, stops: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit">
                حفظ
              </button>
            </div>
          </form>
          <div className="panel table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>المسار</th>
                  <th>الحافلة</th>
                  <th>السائق</th>
                  <th>الطلاب</th>
                </tr>
              </thead>
              <tbody>
                {routeResults.map((r) => (
                  <tr key={r.id}>
                    <td>{r.name}</td>
                    <td>{r.bus_number || '—'}</td>
                    <td>
                      {r.driver_name || '—'} {r.driver_phone ? `(${r.driver_phone})` : ''}
                    </td>
                    <td>{r.student_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === 'drivers' && (
        <>
          <form className="panel form-grid" onSubmit={submitDriver}>
            <h3>إضافة سائق</h3>
            <label>
              الاسم *
              <input
                required
                value={driverForm.name}
                onChange={(e) => setDriverForm({ ...driverForm, name: e.target.value })}
              />
            </label>
            <label>
              الهاتف
              <input
                value={driverForm.phone}
                onChange={(e) => setDriverForm({ ...driverForm, phone: e.target.value })}
              />
            </label>
            <label>
              رقم الرخصة
              <input
                value={driverForm.license_number}
                onChange={(e) => setDriverForm({ ...driverForm, license_number: e.target.value })}
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit">
                حفظ
              </button>
            </div>
          </form>
          <div className="panel table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>الاسم</th>
                  <th>الهاتف</th>
                  <th>الرخصة</th>
                </tr>
              </thead>
              <tbody>
                {driverResults.map(
                  (d: { id: number; name: string; phone: string; license_number: string }) => (
                    <tr key={d.id}>
                      <td>{d.name}</td>
                      <td>{d.phone || '—'}</td>
                      <td>{d.license_number || '—'}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
