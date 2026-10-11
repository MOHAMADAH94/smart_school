import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import * as authApi from '../api/auth';
import * as schoolsApi from '../api/schools';
import type { Membership, SchoolContext, User } from '../types';

interface AuthState {
  user: User | null;
  memberships: Membership[];
  schoolContext: SchoolContext | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (payload: authApi.RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshContext: () => Promise<void>;
  setCurrentSchool: (schoolId: number) => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [schoolContext, setSchoolContext] = useState<SchoolContext | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshContext = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setUser(null);
      setMemberships([]);
      setSchoolContext(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.fetchMe();
      setUser(me.user);
      setMemberships(me.memberships);
      if (me.memberships.length > 0) {
        const stored = localStorage.getItem('current_school_id');
        const valid = me.memberships.some((m) => String(m.school.id) === stored);
        if (!valid) {
          localStorage.setItem('current_school_id', String(me.memberships[0].school.id));
        }
        const activeMembership =
          me.memberships.find((m) => String(m.school.id) === localStorage.getItem('current_school_id')) ||
          me.memberships[0];
        localStorage.setItem('current_role', activeMembership.role);
        try {
          const ctx = await schoolsApi.fetchSchoolContext();
          setSchoolContext(ctx);
          if (ctx.membership?.role) {
            localStorage.setItem('current_role', ctx.membership.role);
          }
        } catch {
          // Keep the session even if school context fails; avoid silent logout.
          setSchoolContext({
            has_school: true,
            membership: me.memberships[0],
            permissions: me.memberships[0].permissions ?? [],
            features: [],
            school: me.memberships[0].school,
          });
        }
      } else {
        localStorage.removeItem('current_school_id');
        localStorage.removeItem('current_role');
        setSchoolContext({
          has_school: false,
          membership: null,
          permissions: [],
          features: [],
        });
      }
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('current_school_id');
      localStorage.removeItem('current_role');
      setUser(null);
      setMemberships([]);
      setSchoolContext(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshContext();
  }, [refreshContext]);

  const login = useCallback(
    async (username: string, password: string) => {
      const data = await authApi.login(username, password);
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      setLoading(true);
      await refreshContext();
    },
    [refreshContext],
  );

  const register = useCallback(async (payload: authApi.RegisterPayload) => {
    await authApi.register(payload);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('current_school_id');
    localStorage.removeItem('current_role');
    setUser(null);
    setMemberships([]);
    setSchoolContext(null);
  }, []);

  const setCurrentSchool = useCallback(
    async (schoolId: number) => {
      localStorage.setItem('current_school_id', String(schoolId));
      await refreshContext();
    },
    [refreshContext],
  );

  const value = useMemo(
    () => ({
      user,
      memberships,
      schoolContext,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
      refreshContext,
      setCurrentSchool,
    }),
    [
      user,
      memberships,
      schoolContext,
      loading,
      login,
      register,
      logout,
      refreshContext,
      setCurrentSchool,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
