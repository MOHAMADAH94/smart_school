/** Format numeric values for UI display (2 decimal places). */
export function formatNumber(value: unknown, digits = 2): string {
  if (value == null || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(n)) return '—';
  return n.toFixed(digits);
}
