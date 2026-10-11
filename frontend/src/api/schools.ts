import { api } from './client';
import type { Membership, School, SchoolContext } from '../types';

export interface CreateSchoolPayload {
  name: string;
  phone?: string;
  email?: string;
  address?: string;
  city?: string;
  country?: string;
  academic_year?: string;
}

export async function createSchool(payload: CreateSchoolPayload) {
  const { data } = await api.post<{
    message: string;
    school: School;
    membership: Membership;
  }>('/schools/create/', payload);
  return data;
}

export async function fetchSchoolContext() {
  const { data } = await api.get<SchoolContext>('/schools/current/');
  return data;
}

export async function fetchMySchools() {
  const { data } = await api.get<{ results?: School[] } | School[]>('/schools/');
  return Array.isArray(data) ? data : data.results ?? [];
}
