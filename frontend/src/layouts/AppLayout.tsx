import { NavLink, Outlet } from 'react-router-dom';
import { NotificationBell } from '../components/NotificationBell';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { isSchoolManager } from '../utils/roles';

export function AppLayout() {
  const { user, schoolContext, memberships, logout, setCurrentSchool } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const permissions = new Set(schoolContext?.permissions ?? []);
  const features = new Set(schoolContext?.features ?? []);
  const role = schoolContext?.membership?.role;
  const manager = isSchoolManager(role);

  const navItems = [
    {
      to: '/dashboard',
      label: 'لوحة التحكم',
      show: manager && permissions.has('dashboard.view'),
    },
    {
      to: '/my-class',
      label: 'فصلي',
      show: role === 'TEACHER',
    },
    {
      to: '/my-children',
      label: 'أبنائي',
      show: role === 'PARENT',
    },
    {
      to: '/students',
      label: role === 'TEACHER' ? 'طلاب فصلي' : 'الطلاب',
      show: permissions.has('students.view') && features.has('students') && role !== 'PARENT',
    },
    {
      to: '/teachers',
      label: 'المعلمون',
      show: manager && permissions.has('teachers.view') && features.has('teachers'),
    },
    {
      to: '/classes',
      label: 'الفصول',
      show: (manager || role === 'TEACHER') && permissions.has('classes.view') && features.has('classes'),
    },
    {
      to: '/subjects',
      label: 'المواد',
      show: (manager || role === 'TEACHER') && permissions.has('subjects.view') && features.has('subjects'),
    },
    {
      to: '/attendance',
      label: 'الحضور',
      show: (manager || role === 'TEACHER') && permissions.has('attendance.view') && features.has('attendance'),
    },
    {
      to: '/grades',
      label: 'الدرجات',
      show: (manager || role === 'TEACHER') && permissions.has('grades.view') && features.has('grades'),
    },
    {
      to: '/timetable',
      label: 'الجدول الدراسي',
      show: manager && permissions.has('timetable.view') && features.has('timetable'),
    },
    {
      to: '/my-timetable',
      label: 'جدولي',
      show: role === 'TEACHER' && permissions.has('timetable.view') && features.has('timetable'),
    },
    {
      to: '/parents',
      label: 'أولياء الأمور',
      show: manager && permissions.has('parents.view') && features.has('parents'),
    },
    {
      to: '/transport',
      label: 'النقل',
      show: manager && permissions.has('transport.view') && features.has('transport'),
    },
    {
      to: '/finance',
      label: 'المالية',
      show:
        manager &&
        permissions.has('finance.view') &&
        features.has('accounting') &&
        permissions.has('finance.manage'),
    },
    {
      to: '/notifications',
      label: 'الإشعارات',
      show: permissions.has('notifications.view') && features.has('notifications'),
    },
    {
      to: '/subscription',
      label: 'الاشتراك',
      show: permissions.has('subscription.manage'),
      disabled: true,
    },
    {
      to: '/settings',
      label: 'الإعدادات',
      show: manager && (permissions.has('school.manage') || permissions.has('school.view')),
      disabled: true,
    },
  ].filter((i) => i.show);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">SS</span>
          <div>
            <strong className="brand-name">المدرسة الذكية</strong>
            <small>Smart School</small>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) =>
            item.disabled ? (
              <span
                key={item.to}
                className="nav-disabled"
                title="قيد التطوير"
                aria-disabled="true"
              >
                {item.label}
                <small>قيد التطوير</small>
              </span>
            ) : (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
                {item.label}
              </NavLink>
            ),
          )}
        </nav>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-school">
            {memberships.length > 1 ? (
              <select
                value={schoolContext?.school?.id ?? ''}
                onChange={(e) => void setCurrentSchool(Number(e.target.value))}
                aria-label="تبديل المدرسة"
              >
                {memberships.map((m) => (
                  <option key={m.id} value={m.school.id}>
                    {m.school.name}
                  </option>
                ))}
              </select>
            ) : (
              <h1>{schoolContext?.school?.name ?? 'مدرستي'}</h1>
            )}
          </div>
          <div className="topbar-actions">
            <NotificationBell />
            <button
              type="button"
              className="icon-btn"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'الوضع النهاري' : 'الوضع الليلي'}
              title={theme === 'dark' ? 'الوضع النهاري' : 'الوضع الليلي'}
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
            <div className="user-chip">
              <span>{user?.first_name || user?.username}</span>
              <small>{schoolContext?.membership?.role_display}</small>
            </div>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              خروج
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
