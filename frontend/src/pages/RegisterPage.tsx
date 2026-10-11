import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function RegisterPage() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: '',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await register(form);
      await login(form.username, form.password);
      navigate('/create-school');
    } catch (err: unknown) {
      const ax = err as { response?: { data?: Record<string, unknown> } };
      const data = ax.response?.data;
      if (data) {
        const first = Object.values(data)[0];
        setError(Array.isArray(first) ? String(first[0]) : String(first));
      } else {
        setError('تعذر إنشاء الحساب.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <h2>إنشاء حساب</h2>
      <p className="muted">ابدأ بإعداد حساب مالك المدرسة</p>
      {error && <div className="alert error">{error}</div>}
      <div className="form-row">
        <label>
          الاسم الأول
          <input value={form.first_name} onChange={(e) => update('first_name', e.target.value)} />
        </label>
        <label>
          اسم العائلة
          <input value={form.last_name} onChange={(e) => update('last_name', e.target.value)} />
        </label>
      </div>
      <label>
        اسم المستخدم
        <input
          value={form.username}
          onChange={(e) => update('username', e.target.value)}
          required
          autoComplete="username"
        />
      </label>
      <label>
        البريد الإلكتروني
        <input
          type="email"
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
          required
          autoComplete="email"
        />
      </label>
      <label>
        الهاتف
        <input value={form.phone} onChange={(e) => update('phone', e.target.value)} />
      </label>
      <label>
        كلمة المرور
        <input
          type="password"
          value={form.password}
          onChange={(e) => update('password', e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
        />
      </label>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        {submitting ? 'جاري الإنشاء...' : 'إنشاء الحساب'}
      </button>
      <p className="muted center">
        لديك حساب؟ <Link to="/login">سجّل الدخول</Link>
      </p>
    </form>
  );
}
