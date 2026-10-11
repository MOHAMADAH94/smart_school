import { api } from './client';
import type { AuthTokens, Membership, User } from '../types';

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}

export async function register(payload: RegisterPayload) {
  const { data } = await api.post<{ message: string; user: User }>('/auth/register/', payload);
  return data;
}

export async function login(username: string, password: string) {
  const { data } = await api.post<AuthTokens & { user: User }>('/auth/login/', {
    username,
    password,
  });
  return data;
}

export async function fetchMe() {
  const { data } = await api.get<{
    user: User;
    memberships: Membership[];
    current_school_id: number | null;
  }>('/auth/me/');
  return data;
}
