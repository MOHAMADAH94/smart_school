import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import {
  GuestRoute,
  ProtectedRoute,
  RequireManagerDashboard,
  RequireSchool,
} from './components/ProtectedRoute';
import { AppLayout } from './layouts/AppLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { CreateSchoolPage } from './pages/CreateSchoolPage';
import { DashboardPage } from './pages/DashboardPage';
import { StudentsPage } from './pages/StudentsPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { TeachersPage } from './pages/TeachersPage';
import { ClassesPage } from './pages/ClassesPage';
import { SubjectsPage } from './pages/SubjectsPage';
import { ParentsPage } from './pages/ParentsPage';
import { AttendancePage } from './pages/AttendancePage';
import { GradesPage } from './pages/GradesPage';
import { TransportPage } from './pages/TransportPage';
import { FinancePage } from './pages/FinancePage';
import { SubscriptionPage } from './pages/SubscriptionPage';
import { SettingsPage } from './pages/SettingsPage';
import { TeacherClassPage } from './pages/TeacherClassPage';
import { ParentPortalPage } from './pages/ParentPortalPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { TimetablePage } from './pages/TimetablePage';
import { MyTimetablePage } from './pages/MyTimetablePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<GuestRoute />}>
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute />}>
                <Route path="/create-school" element={<CreateSchoolPage />} />
                <Route element={<RequireSchool />}>
                  <Route element={<AppLayout />}>
                    <Route element={<RequireManagerDashboard />}>
                      <Route path="/dashboard" element={<DashboardPage />} />
                    </Route>
                    <Route path="/my-class" element={<TeacherClassPage />} />
                    <Route path="/my-children" element={<ParentPortalPage />} />
                    <Route path="/students" element={<StudentsPage />} />
                    <Route path="/students/:id" element={<StudentDetailPage />} />
                    <Route path="/teachers" element={<TeachersPage />} />
                    <Route path="/classes" element={<ClassesPage />} />
                    <Route path="/subjects" element={<SubjectsPage />} />
                    <Route path="/parents" element={<ParentsPage />} />
                    <Route path="/attendance" element={<AttendancePage />} />
                    <Route path="/grades" element={<GradesPage />} />
                    <Route path="/timetable" element={<TimetablePage />} />
                    <Route path="/my-timetable" element={<MyTimetablePage />} />
                    <Route path="/transport" element={<TransportPage />} />
                    <Route path="/transport/buses" element={<TransportPage />} />
                    <Route path="/transport/routes" element={<TransportPage />} />
                    <Route path="/finance" element={<FinancePage />} />
                    <Route path="/finance/fees" element={<FinancePage />} />
                    <Route path="/finance/payments" element={<FinancePage />} />
                    <Route path="/finance/expenses" element={<FinancePage />} />
                    <Route path="/notifications" element={<NotificationsPage />} />
                    <Route path="/subscription" element={<SubscriptionPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                  </Route>
                </Route>
              </Route>

              <Route path="/" element={<Navigate to="/login" replace />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
