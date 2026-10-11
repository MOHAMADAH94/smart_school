export type Role =
  | 'SUPER_ADMIN'
  | 'SCHOOL_OWNER'
  | 'SCHOOL_ADMIN'
  | 'ACCOUNTANT'
  | 'TEACHER'
  | 'PARENT'
  | 'STUDENT';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  preferred_language: string;
  date_joined: string;
}

export interface School {
  id: number;
  name: string;
  logo: string | null;
  phone: string;
  email: string;
  address: string;
  city: string;
  country: string;
  academic_year: string;
  school_code: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: number;
  school: School;
  role: Role;
  role_display: string;
  is_active: boolean;
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface SchoolContext {
  has_school: boolean;
  membership: Membership | null;
  permissions: string[];
  features: string[];
  school?: School;
}
