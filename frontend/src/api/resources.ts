import { api } from './client';

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Student {
  id: number;
  student_code: string;
  first_name: string;
  father_name: string;
  last_name: string;
  full_name: string;
  gender: string;
  date_of_birth: string | null;
  phone: string;
  address: string;
  enrollment_date: string | null;
  status: string;
  classroom: number | null;
  classroom_name: string | null;
  notes: string;
}

export interface Teacher {
  id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  email: string;
  specialization: string;
  hire_date: string | null;
  status: string;
  notes: string;
  has_login?: boolean;
  login_username?: string | null;
}

export interface Parent {
  id: number;
  name: string;
  phone: string;
  email: string;
  address: string;
  relationship: string;
  has_login?: boolean;
  login_username?: string | null;
}

export interface GradeLevel {
  id: number;
  name: string;
  order: number;
}

export interface Classroom {
  id: number;
  name: string;
  section: string;
  capacity: number | null;
  grade_level: number;
  grade_level_name: string;
  student_count: number;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  description: string;
}

export interface TransportAssignment {
  id: number;
  student: number;
  student_name?: string;
  bus: number;
  bus_number?: string;
  route: number;
  route_name?: string;
  pickup_location: string;
  dropoff_location: string;
  monthly_fee: string | number;
  status: string;
  notes: string;
}

async function listResource<T>(path: string, params?: Record<string, string>) {
  const { data } = await api.get<Paginated<T> | T[]>(path, { params });
  if (Array.isArray(data)) return { count: data.length, results: data };
  return data;
}

export const studentsApi = {
  list: (params?: Record<string, string>) => listResource<Student>('/students/', params),
  get: async (id: number) => (await api.get<Student>(`/students/${id}/`)).data,
  profile: async (id: number) => (await api.get(`/students/${id}/profile/`)).data,
  create: async (payload: Partial<Student>) => (await api.post<Student>('/students/', payload)).data,
  update: async (id: number, payload: Partial<Student>) =>
    (await api.patch<Student>(`/students/${id}/`, payload)).data,
  remove: async (id: number) => api.delete(`/students/${id}/`),
};

export const teachersApi = {
  list: (params?: Record<string, string>) => listResource<Teacher>('/teachers/', params),
  create: async (payload: Partial<Teacher> & { username?: string; password?: string }) =>
    (await api.post<Teacher>('/teachers/', payload)).data,
  update: async (id: number, payload: Partial<Teacher> & { username?: string; password?: string }) =>
    (await api.patch<Teacher>(`/teachers/${id}/`, payload)).data,
  createLogin: async (id: number, payload: { username: string; password: string }) =>
    (await api.post<Teacher>(`/teachers/${id}/create-login/`, payload)).data,
  remove: async (id: number) => api.delete(`/teachers/${id}/`),
  myClasses: async () => (await api.get('/teachers/my-classes/')).data,
};

export const parentsApi = {
  list: (params?: Record<string, string>) => listResource<Parent>('/parents/', params),
  create: async (payload: Partial<Parent> & { username?: string; password?: string }) =>
    (await api.post<Parent>('/parents/', payload)).data,
  update: async (id: number, payload: Partial<Parent> & { username?: string; password?: string }) =>
    (await api.patch<Parent>(`/parents/${id}/`, payload)).data,
  createLogin: async (id: number, payload: { username: string; password: string }) =>
    (await api.post<Parent>(`/parents/${id}/create-login/`, payload)).data,
  remove: async (id: number) => api.delete(`/parents/${id}/`),
  myChildren: async () => (await api.get('/parents/my-children/')).data,
  listLinks: (params?: Record<string, string>) =>
    listResource<any>('/parents/links/student-parents/', params),
  linkStudent: async (payload: {
    student: number;
    parent: number;
    relationship: string;
    is_primary?: boolean;
  }) => (await api.post('/parents/links/student-parents/', payload)).data,
  unlinkStudent: async (id: number) => api.delete(`/parents/links/student-parents/${id}/`),
};

export const classesApi = {
  listGrades: () => listResource<GradeLevel>('/classes/grades/'),
  createGrade: async (payload: Partial<GradeLevel>) =>
    (await api.post<GradeLevel>('/classes/grades/', payload)).data,
  updateGrade: async (id: number, payload: Partial<GradeLevel>) =>
    (await api.patch<GradeLevel>(`/classes/grades/${id}/`, payload)).data,
  removeGrade: async (id: number) => api.delete(`/classes/grades/${id}/`),
  listClassrooms: (params?: Record<string, string>) =>
    listResource<Classroom>('/classes/', params),
  createClassroom: async (payload: Partial<Classroom>) =>
    (await api.post<Classroom>('/classes/', payload)).data,
  updateClassroom: async (id: number, payload: Partial<Classroom>) =>
    (await api.patch<Classroom>(`/classes/${id}/`, payload)).data,
  removeClassroom: async (id: number) => api.delete(`/classes/${id}/`),
};

export const subjectsApi = {
  list: (params?: Record<string, string>) => listResource<Subject>('/subjects/', params),
  create: async (payload: Partial<Subject>) => (await api.post<Subject>('/subjects/', payload)).data,
  update: async (id: number, payload: Partial<Subject>) =>
    (await api.patch<Subject>(`/subjects/${id}/`, payload)).data,
  remove: async (id: number) => api.delete(`/subjects/${id}/`),
  listAssignments: (params?: Record<string, string>) =>
    listResource<any>('/subjects/assignments/', params),
  createAssignment: async (payload: {
    teacher: number;
    subject: number;
    classroom: number;
  }) => (await api.post('/subjects/assignments/', payload)).data,
  removeAssignment: async (id: number) => api.delete(`/subjects/assignments/${id}/`),
};

export const gradesApi = {
  list: (params?: Record<string, string>) => listResource<any>('/grades/', params),
  listTerms: () => listResource<any>('/grades/terms/'),
  createTerm: async (payload: Record<string, unknown>) =>
    (await api.post('/grades/terms/', payload)).data,
  listAssessments: (params?: Record<string, string>) =>
    listResource<any>('/grades/assessments/', params),
  createAssessment: async (payload: Record<string, unknown>) =>
    (await api.post('/grades/assessments/', payload)).data,
  bulk: async (payload: {
    assessment_id: number;
    records: { student_id: number; score: number | string; notes?: string }[];
  }) => (await api.post('/grades/bulk/', payload)).data,
  report: async (params?: Record<string, string>) =>
    (await api.get('/grades/report/', { params })).data,
  gradebook: async (params: Record<string, string>) =>
    (await api.get('/grades/gradebook/', { params })).data,
};

export const transportApi = {
  listBuses: () => listResource<any>('/transport/buses/'),
  listRoutes: () => listResource<any>('/transport/routes/'),
  listDrivers: () => listResource<any>('/transport/drivers/'),
  listAssignments: (params?: Record<string, string>) =>
    listResource<TransportAssignment>('/transport/assignments/', params),
  createAssignment: async (payload: Partial<TransportAssignment>) =>
    (await api.post<TransportAssignment>('/transport/assignments/', payload)).data,
  updateAssignment: async (id: number, payload: Partial<TransportAssignment>) =>
    (await api.patch<TransportAssignment>(`/transport/assignments/${id}/`, payload)).data,
  removeAssignment: async (id: number) => api.delete(`/transport/assignments/${id}/`),
};

export type AppNotification = {
  id: number;
  type: string;
  audience?: string;
  audience_label?: string;
  title: string;
  body: string;
  is_read: boolean;
  user?: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export const notificationsApi = {
  list: (params?: Record<string, string>) =>
    listResource<AppNotification>('/notifications/', params),
  unreadCount: async () =>
    (await api.get<{ count: number }>('/notifications/unread_count/')).data.count,
  markRead: async (id: number) =>
    (await api.post<AppNotification>(`/notifications/${id}/mark_read/`)).data,
  markAllRead: async () => (await api.post('/notifications/mark_all_read/')).data,
  create: async (
    payload: Partial<AppNotification> & { title: string; audience?: string; type?: string },
  ) => (await api.post<AppNotification>('/notifications/', payload)).data,
};

export interface Timetable {
  id: number;
  name: string;
  academic_year: string;
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED' | string;
  working_days: number[];
  period_duration_minutes: number;
  notes: string;
  published_at: string | null;
  entries_count?: number;
  requirements_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TimetablePeriod {
  id: number;
  timetable?: number;
  period_number: number;
  label: string;
  start_time: string;
  end_time: string;
  is_break: boolean;
}

export interface TimetableEntry {
  id: number;
  timetable: number;
  day: number;
  period: number;
  period_number?: number;
  period_label?: string;
  start_time?: string;
  end_time?: string;
  classroom: number;
  classroom_name?: string;
  subject: number;
  subject_name?: string;
  teaching_assignment: number;
  teacher_name?: string;
}

export const timetableApi = {
  list: (params?: Record<string, string>) => listResource<Timetable>('/timetables/', params),
  get: async (id: number) => (await api.get<Timetable>(`/timetables/${id}/`)).data,
  create: async (payload: Partial<Timetable> & { name: string; academic_year: string }) =>
    (await api.post<Timetable>('/timetables/', payload)).data,
  update: async (id: number, payload: Partial<Timetable>) =>
    (await api.patch<Timetable>(`/timetables/${id}/`, payload)).data,
  remove: async (id: number) => api.delete(`/timetables/${id}/`),
  grid: async (id: number, params?: Record<string, string>) =>
    (
      await api.get<{
        timetable: Timetable;
        periods: TimetablePeriod[];
        entries: TimetableEntry[];
        working_days: number[];
      }>(`/timetables/${id}/grid/`, { params })
    ).data,
  validate: async (id: number) => (await api.get(`/timetables/${id}/validate/`)).data,
  generate: async (
    id: number,
    payload: { apply?: boolean; replace_existing?: boolean } = {},
  ) => (await api.post(`/timetables/${id}/generate/`, payload)).data,
  publish: async (id: number) => (await api.post<Timetable>(`/timetables/${id}/publish/`)).data,
  archive: async (id: number) => (await api.post<Timetable>(`/timetables/${id}/archive/`)).data,
  my: async () =>
    (
      await api.get<{ timetable: Timetable | null; entries: TimetableEntry[] }>(
        '/timetables/my/',
      )
    ).data,
  forClass: async (classroomId: number, params?: Record<string, string>) =>
    (await api.get(`/timetables/class/${classroomId}/`, { params })).data,
  child: async (studentId: number) => (await api.get(`/timetables/child/${studentId}/`)).data,
  listRequirements: (params?: Record<string, string>) =>
    listResource<any>('/timetables/requirements/', params),
  createRequirement: async (payload: Record<string, unknown>) =>
    (await api.post('/timetables/requirements/', payload)).data,
  removeRequirement: async (id: number) => api.delete(`/timetables/requirements/${id}/`),
  createEntry: async (payload: Record<string, unknown>) =>
    (await api.post<TimetableEntry>('/timetables/entries/', payload)).data,
  removeEntry: async (id: number) => api.delete(`/timetables/entries/${id}/`),
  moveEntry: async (id: number, payload: { day: number; period: number }) =>
    (await api.post<TimetableEntry>(`/timetables/entries/${id}/move/`, payload)).data,
  listPeriods: (params?: Record<string, string>) =>
    listResource<TimetablePeriod>('/timetables/periods/', params),
};
