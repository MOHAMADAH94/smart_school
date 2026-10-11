import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { homePathForRole } from '../utils/roles';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      const role = localStorage.getItem('current_role');
      navigate(homePathForRole(role), { replace: true });
    } catch {
      setError('بيانات الدخول غير صحيحة.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <h2>تسجيل الدخول</h2>
      <p className="muted">ادخل إلى حسابك لإدارة مدرستك</p>
      {error && <div className="alert error">{error}</div>}
      <label>
        اسم المستخدم
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
      </label>
      <label>
        كلمة المرور
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </label>
      <button className="btn btn-primary" type="submit" disabled={submitting}>
        {submitting ? 'جاري الدخول...' : 'دخول'}
      </button>
      <p className="muted center">
        ليس لديك حساب؟ <Link to="/register">سجّل الآن</Link>
      </p>
    </form>
  );
}
