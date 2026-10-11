import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { homePathForRole, isSchoolManager } from '../utils/roles';

export function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>جاري التحميل...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function GuestRoute() {
  const { isAuthenticated, loading, schoolContext } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (isAuthenticated) {
    if (schoolContext?.has_school) {
      return <Navigate to={homePathForRole(schoolContext.membership?.role)} replace />;
    }
    return <Navigate to="/create-school" replace />;
  }

  return <Outlet />;
}

export function RequireSchool() {
  const { schoolContext, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (!schoolContext?.has_school) {
    return <Navigate to="/create-school" replace />;
  }

  return <Outlet />;
}

/** Dashboard is for school managers only. */
export function RequireManagerDashboard() {
  const { schoolContext, loading } = useAuth();
  const role = schoolContext?.membership?.role;

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  if (!isSchoolManager(role)) {
    return <Navigate to={homePathForRole(role)} replace />;
  }

  return <Outlet />;
}
