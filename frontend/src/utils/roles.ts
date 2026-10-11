/** Role-aware default landing path after login. */
export function homePathForRole(role?: string | null): string {
  switch (role) {
    case 'TEACHER':
      return '/my-class';
    case 'PARENT':
      return '/my-children';
    case 'STUDENT':
      return '/students';
    default:
      return '/dashboard';
  }
}

export function isSchoolManager(role?: string | null): boolean {
  return role === 'SCHOOL_OWNER' || role === 'SCHOOL_ADMIN' || role === 'SUPER_ADMIN' || role === 'ACCOUNTANT';
}
