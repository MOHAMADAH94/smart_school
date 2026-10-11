import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { teachersApi, type Teacher } from '../api/resources';
import { PaginationBar } from '../components/PaginationBar';
import { useAuth } from '../context/AuthContext';

const PAGE_SIZE = 20;

const emptyForm = {
  employee_code: '',
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  specialization: '',
  status: 'ACTIVE',
  notes: '',
  username: '',
  password: '',
};

export function TeachersPage() {
  const { schoolContext } = useAuth();
  const canManage = (schoolContext?.permissions ?? []).includes('teachers.manage');
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loginFor, setLoginFor] = useState<Teacher | null>(null);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [form, setForm] = useState(emptyForm);

  const { data, isLoading } = useQuery({
    queryKey: ['teachers', search, page],
    queryFn: () =>
      teachersApi.list({
        page: String(page),
        page_size: String(PAGE_SIZE),
        ...(search ? { search } : {}),
      }),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        employee_code: form.employee_code,
        first_name: form.first_name,
        last_name: form.last_name,
        phone: form.phone,
        email: form.email,
        specialization: form.specialization,
        status: form.status,
        notes: form.notes,
        ...(!editingId && form.username.trim()
          ? { username: form.username.trim(), password: form.password }
          : {}),
      };
      if (editingId) return teachersApi.update(editingId, payload);
      return teachersApi.create(payload);
    },
    onSuccess: async () => {
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      setError('');
      await qc.invalidateQueries({ queryKey: ['teachers'] });
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg =
        (data?.username as string[] | string | undefined) ||
        (data?.password as string[] | string | undefined) ||
        data?.detail ||
        'تعذر حفظ المعلم.';
      setError(Array.isArray(msg) ? msg[0] : String(msg));
    },
  });

  const loginMutation = useMutation({
    mutationFn: () =>
      teachersApi.createLogin(loginFor!.id, {
        username: loginForm.username.trim(),
        password: loginForm.password,
      }),
    onSuccess: async () => {
      setLoginFor(null);
      setLoginForm({ username: '', password: '' });
      setError('');
      await qc.invalidateQueries({ queryKey: ['teachers'] });
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg =
        (data?.username as string[] | string | undefined) ||
        (data?.password as string[] | string | undefined) ||
        data?.detail ||
        'تعذر إنشاء حساب الدخول.';
      setError(Array.isArray(msg) ? msg[0] : String(msg));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => teachersApi.remove(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['teachers'] });
    },
  });

  function openEdit(t: Teacher) {
    setEditingId(t.id);
    setForm({
      employee_code: t.employee_code,
      first_name: t.first_name,
      last_name: t.last_name,
      phone: t.phone || '',
      email: t.email || '',
      specialization: t.specialization || '',
      status: t.status,
      notes: t.notes || '',
      username: '',
      password: '',
    });
    setShowForm(true);
    setError('');
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    saveMutation.mutate();
  }

  function onLogin(e: FormEvent) {
    e.preventDefault();
    loginMutation.mutate();
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>المعلمون</h2>
          <p className="muted">إضافة · تعديل · إنشاء حساب دخول لبوابة المعلم</p>
        </div>
        {canManage && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setEditingId(null);
              setForm(emptyForm);
              setShowForm(true);
              setError('');
            }}
          >
            إضافة معلم
          </button>
        )}
      </header>

      <div className="toolbar">
        <input
          placeholder="بحث..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {error && <div className="alert error">{error}</div>}

      {showForm && canManage && (
        <form className="panel form-grid" onSubmit={onSubmit}>
          <h3>{editingId ? 'تعديل معلم' : 'معلم جديد'}</h3>
          <label>
            الرمز الوظيفي *
            <input
              required
              value={form.employee_code}
              onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
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
            اسم العائلة *
            <input
              required
              value={form.last_name}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </label>
          <label>
            التخصص
            <input
              value={form.specialization}
              onChange={(e) => setForm({ ...form, specialization: e.target.value })}
            />
          </label>
          <label>
            الهاتف
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          <label>
            البريد
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </label>
          <label>
            الحالة
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="ACTIVE">نشط</option>
              <option value="INACTIVE">غير نشط</option>
              <option value="ON_LEAVE">إجازة</option>
            </select>
          </label>
          <label className="full">
            ملاحظات
            <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </label>
          {!editingId && (
            <>
              <label>
                اسم المستخدم (اختياري)
                <input
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  autoComplete="off"
                />
              </label>
              <label>
                كلمة المرور
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  autoComplete="new-password"
                  minLength={form.username.trim() ? 8 : undefined}
                />
              </label>
            </>
          )}
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={saveMutation.isPending}>
              حفظ
            </button>
            <button
              className="btn btn-ghost"
              type="button"
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

      {loginFor && canManage && (
        <form className="panel form-grid" onSubmit={onLogin}>
          <h3>
            {loginFor.has_login ? 'تغيير كلمة المرور' : 'إنشاء حساب دخول'} — {loginFor.full_name}
          </h3>
          <label>
            اسم المستخدم *
            <input
              required
              value={loginForm.username}
              onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
              autoComplete="off"
            />
          </label>
          <label>
            كلمة المرور {loginFor.has_login ? '(اتركها فارغة للإبقاء)' : '*'}
            <input
              type="password"
              required={!loginFor.has_login}
              minLength={8}
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              autoComplete="new-password"
            />
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={loginMutation.isPending}>
              حفظ الحساب
            </button>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => {
                setLoginFor(null);
                setLoginForm({ username: '', password: '' });
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
                <th>التخصص</th>
                <th>الهاتف</th>
                <th>حساب الدخول</th>
                <th>الحالة</th>
                <th>إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((t) => (
                <tr key={t.id}>
                  <td>{t.employee_code}</td>
                  <td>{t.full_name}</td>
                  <td>{t.specialization || '—'}</td>
                  <td>{t.phone || '—'}</td>
                  <td>
                    {t.has_login ? t.login_username : <span className="muted">بدون حساب</span>}
                  </td>
                  <td>{t.status}</td>
                  <td className="actions-cell">
                    {canManage && (
                      <>
                        <button
                          type="button"
                          className="link-btn"
                          onClick={() => {
                            setLoginFor(t);
                            setLoginForm({ username: t.login_username || '', password: '' });
                            setError('');
                          }}
                        >
                          {t.has_login ? 'تغيير كلمة المرور' : 'إنشاء حساب دخول'}
                        </button>
                        <button type="button" className="link-btn" onClick={() => openEdit(t)}>
                          تعديل
                        </button>
                        <button
                          type="button"
                          className="link-btn danger"
                          onClick={() => {
                            if (confirm('حذف هذا المعلم؟')) deleteMutation.mutate(t.id);
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
                  <td colSpan={7} className="muted">
                    لا يوجد معلمون.
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
          label="معلم"
        />
      </div>
    </div>
  );
}
