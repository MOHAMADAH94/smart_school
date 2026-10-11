import { Link, Outlet } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

export function AuthLayout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <div className="auth-panel-top">
          <div className="auth-brand">
            <span className="brand-mark large">SS</span>
            <h1>المدرسة الذكية</h1>
            <p>منصة إدارة المدارس السحابية</p>
          </div>
          <button
            type="button"
            className="icon-btn"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'الوضع النهاري' : 'الوضع الليلي'}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
                <path
                  d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M20 14.5A7.5 7.5 0 1 1 9.5 4a6 6 0 1 0 10.5 10.5Z"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
        <Outlet />
        <p className="auth-footer">
          <Link to="/login">تسجيل الدخول</Link>
          <span>·</span>
          <Link to="/register">إنشاء حساب</Link>
        </p>
      </div>
      <div className="auth-visual" aria-hidden="true">
        <div className="auth-visual-content">
          <h2>إدارة مدرستك بثقة</h2>
          <p>طلاب · معلمون · حضور · درجات · نقل · مالية</p>
        </div>
      </div>
    </div>
  );
}
