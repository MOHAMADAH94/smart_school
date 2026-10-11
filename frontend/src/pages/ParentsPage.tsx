import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { parentsApi, studentsApi, type Parent } from '../api/resources';
import { PaginationBar } from '../components/PaginationBar';
import { useAuth } from '../context/AuthContext';

const PAGE_SIZE = 20;

const emptyForm = {
  name: '',
  phone: '',
  email: '',
  address: '',
  relationship: 'FATHER',
  username: '',
  password: '',
};

export function ParentsPage() {
  const { schoolContext } = useAuth();
  const canManage = (schoolContext?.permissions ?? []).includes('parents.manage');
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [showLink, setShowLink] = useState(false);
  const [loginFor, setLoginFor] = useState<Parent | null>(null);
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [linkForm, setLinkForm] = useState({
    parent: '',
    student: '',
    relationship: 'FATHER',
    is_primary: true,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['parents', search, page],
    queryFn: () =>
      parentsApi.list({
        page: String(page),
        page_size: String(PAGE_SIZE),
        ...(search ? { search } : {}),
      }),
  });

  const students = useQuery({
    queryKey: ['students-for-parent-link'],
    queryFn: () => studentsApi.list({ status: 'ACTIVE', page_size: '200' }),
    enabled: canManage,
  });

  const links = useQuery({
    queryKey: ['student-parent-links'],
    queryFn: () => parentsApi.listLinks({ page_size: '200' }),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      parentsApi.create({
        name: form.name,
        phone: form.phone,
        email: form.email,
        address: form.address,
        relationship: form.relationship,
        ...(form.username.trim()
          ? { username: form.username.trim(), password: form.password }
          : {}),
      }),
    onSuccess: async () => {
      setShowForm(false);
      setForm(emptyForm);
      setError('');
      await qc.invalidateQueries({ queryKey: ['parents'] });
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg =
        (data?.username as string[] | string | undefined) ||
        (data?.password as string[] | string | undefined) ||
        data?.detail ||
        'تعذر إضافة ولي الأمر.';
      setError(Array.isArray(msg) ? msg[0] : String(msg));
    },
  });

  const loginMutation = useMutation({
    mutationFn: () =>
      parentsApi.createLogin(loginFor!.id, {
        username: loginForm.username.trim(),
        password: loginForm.password,
      }),
    onSuccess: async () => {
      setLoginFor(null);
      setLoginForm({ username: '', password: '' });
      setError('');
      await qc.invalidateQueries({ queryKey: ['parents'] });
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

  const linkMutation = useMutation({
    mutationFn: () =>
      parentsApi.linkStudent({
        parent: Number(linkForm.parent),
        student: Number(linkForm.student),
        relationship: linkForm.relationship,
        is_primary: linkForm.is_primary,
      }),
    onSuccess: async () => {
      setShowLink(false);
      setLinkForm({ parent: '', student: '', relationship: 'FATHER', is_primary: true });
      setError('');
      await qc.invalidateQueries({ queryKey: ['student-parent-links'] });
      await qc.invalidateQueries({ queryKey: ['students'] });
    },
    onError: () => setError('تعذر ربط ولي الأمر بالطالب. قد يكون الربط موجوداً مسبقاً.'),
  });

  const unlinkMutation = useMutation({
    mutationFn: (id: number) => parentsApi.unlinkStudent(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['student-parent-links'] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    createMutation.mutate();
  }

  function onLink(e: FormEvent) {
    e.preventDefault();
    linkMutation.mutate();
  }

  function onLogin(e: FormEvent) {
    e.preventDefault();
    loginMutation.mutate();
  }

  return (
    <div className="page">
      <header className="page-header row-between">
        <div>
          <h2>أولياء الأمور</h2>
          <p className="muted">أنشئ حساب دخول لولي الأمر، ثم اربطه بالطالب ليرى بوابة «أبنائي»</p>
        </div>
        {canManage && (
          <div className="row-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setShowLink(true)}>
              ربط بطالب
            </button>
            <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
              إضافة ولي أمر
            </button>
          </div>
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
          <h3>ولي أمر جديد</h3>
          <label>
            الاسم *
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            الصلة الافتراضية
            <select
              value={form.relationship}
              onChange={(e) => setForm({ ...form, relationship: e.target.value })}
            >
              <option value="FATHER">أب</option>
              <option value="MOTHER">أم</option>
              <option value="GUARDIAN">وصي</option>
              <option value="OTHER">أخرى</option>
            </select>
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
            اسم المستخدم (للدخول)
            <input
              autoComplete="off"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder="مثال: parent_ahmed"
            />
          </label>
          <label>
            كلمة المرور
            <input
              type="password"
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="8 أحرف على الأقل"
            />
          </label>
          <p className="muted full">
            اترك حقول الدخول فارغة إذا أردت إضافة الملف فقط، ثم أنشئ الحساب لاحقاً من القائمة.
          </p>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={createMutation.isPending}>
              حفظ
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setShowForm(false)}>
              إلغاء
            </button>
          </div>
        </form>
      )}

      {loginFor && canManage && (
        <form className="panel form-grid" onSubmit={onLogin}>
          <h3>
            {loginFor.has_login ? 'تحديث حساب الدخول' : 'إنشاء حساب دخول'} — {loginFor.name}
          </h3>
          <label>
            اسم المستخدم *
            <input
              required
              autoComplete="off"
              value={loginForm.username}
              onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
            />
          </label>
          <label>
            كلمة المرور *
            <input
              required
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
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

      {showLink && canManage && (
        <form className="panel form-grid" onSubmit={onLink}>
          <h3>ربط ولي أمر بطالب</h3>
          <label>
            ولي الأمر *
            <select
              required
              value={linkForm.parent}
              onChange={(e) => setLinkForm({ ...linkForm, parent: e.target.value })}
            >
              <option value="">اختر ولي الأمر</option>
              {(data?.results ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.has_login ? ` (${p.login_username})` : ''}
                </option>
              ))}
            </select>
          </label>
          <label>
            الطالب *
            <select
              required
              value={linkForm.student}
              onChange={(e) => setLinkForm({ ...linkForm, student: e.target.value })}
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
            الصلة *
            <select
              value={linkForm.relationship}
              onChange={(e) => setLinkForm({ ...linkForm, relationship: e.target.value })}
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
              value={linkForm.is_primary ? '1' : '0'}
              onChange={(e) => setLinkForm({ ...linkForm, is_primary: e.target.value === '1' })}
            >
              <option value="1">نعم</option>
              <option value="0">لا</option>
            </select>
          </label>
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={linkMutation.isPending}>
              ربط
            </button>
            <button className="btn btn-ghost" type="button" onClick={() => setShowLink(false)}>
              إلغاء
            </button>
          </div>
        </form>
      )}

      <div className="panel table-wrap">
        <h3>أولياء الأمور</h3>
        {isLoading ? (
          <p className="muted">جاري التحميل...</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>الاسم</th>
                <th>الصلة</th>
                <th>الهاتف</th>
                <th>حساب الدخول</th>
                {canManage && <th>إجراءات</th>}
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.relationship}</td>
                  <td>{p.phone || '—'}</td>
                  <td>{p.has_login ? p.login_username : <span className="muted">بدون حساب</span>}</td>
                  {canManage && (
                    <td className="actions-cell">
                      <button
                        type="button"
                        className="link-btn"
                        onClick={() => {
                          setLoginFor(p);
                          setLoginForm({ username: p.login_username || '', password: '' });
                          setError('');
                        }}
                      >
                        {p.has_login ? 'تغيير كلمة المرور' : 'إنشاء حساب دخول'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <PaginationBar
          page={page}
          pageSize={PAGE_SIZE}
          count={data?.count ?? 0}
          onPageChange={setPage}
          label="ولي أمر"
        />
      </div>

      <div className="panel table-wrap">
        <h3>روابط الطلاب</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>ولي الأمر</th>
              <th>الطالب</th>
              <th>الصلة</th>
              <th>أساسي</th>
              {canManage && <th>إجراءات</th>}
            </tr>
          </thead>
          <tbody>
            {(links.data?.results ?? []).map(
              (l: {
                id: number;
                parent_detail?: { name: string };
                student_name: string;
                relationship: string;
                is_primary: boolean;
              }) => (
                <tr key={l.id}>
                  <td>{l.parent_detail?.name || '—'}</td>
                  <td>{l.student_name}</td>
                  <td>{l.relationship}</td>
                  <td>{l.is_primary ? 'نعم' : 'لا'}</td>
                  {canManage && (
                    <td>
                      <button
                        type="button"
                        className="link-btn danger"
                        onClick={() => {
                          if (confirm('إلغاء هذا الربط؟')) unlinkMutation.mutate(l.id);
                        }}
                      >
                        إلغاء
                      </button>
                    </td>
                  )}
                </tr>
              ),
            )}
            {(links.data?.results ?? []).length === 0 && (
              <tr>
                <td colSpan={canManage ? 5 : 4} className="muted">
                  لا توجد روابط. استخدم «ربط بطالب».
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
