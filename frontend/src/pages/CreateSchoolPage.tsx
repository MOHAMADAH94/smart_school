import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom';
import { createSchool } from '../api/schools';
import { useAuth } from '../context/AuthContext';

export function CreateSchoolPage() {
  const { isAuthenticated, schoolContext, refreshContext, loading } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    country: 'السعودية',
    academic_year: '2025-2026',
  });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!loading && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!loading && schoolContext?.has_school) {
    return <Navigate to="/dashboard" replace />;
  }

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const result = await createSchool(form);
      localStorage.setItem('current_school_id', String(result.school.id));
      await refreshContext();
      navigate('/dashboard');
    } catch {
      setError('تعذر إنشاء المدرسة. تحقق من البيانات وحاول مرة أخرى.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <div className="auth-brand compact">
          <span className="brand-mark">SS</span>
          <div>
            <h1>المدرسة الذكية</h1>
            <p>أنشئ مدرستك للبدء</p>
          </div>
        </div>
        <form className="auth-form flat" onSubmit={onSubmit}>
          <h2>معلومات المدرسة</h2>
          {error && <div className="alert error">{error}</div>}
          <label>
            اسم المدرسة *
            <input
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              required
              placeholder="مثال: مدرسة الأمل الأهلية"
            />
          </label>
          <div className="form-row">
            <label>
              المدينة
              <input value={form.city} onChange={(e) => update('city', e.target.value)} />
            </label>
            <label>
              الدولة
              <input value={form.country} onChange={(e) => update('country', e.target.value)} />
            </label>
          </div>
          <div className="form-row">
            <label>
              الهاتف
              <input value={form.phone} onChange={(e) => update('phone', e.target.value)} />
            </label>
            <label>
              البريد
              <input
                type="email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
              />
            </label>
          </div>
          <label>
            العنوان
            <input value={form.address} onChange={(e) => update('address', e.target.value)} />
          </label>
          <label>
            العام الدراسي
            <input
              value={form.academic_year}
              onChange={(e) => update('academic_year', e.target.value)}
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'جاري الإنشاء...' : 'إنشاء المدرسة والانتقال للوحة التحكم'}
          </button>
        </form>
      </div>
    </div>
  );
}
