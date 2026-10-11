type Props = {
  page: number;
  pageSize?: number;
  count: number;
  onPageChange: (page: number) => void;
  label?: string;
};

export function PaginationBar({
  page,
  pageSize = 20,
  count,
  onPageChange,
  label = 'سجل',
}: Props) {
  const totalPages = Math.max(1, Math.ceil((count || 0) / pageSize));
  if (!count || totalPages <= 1) {
    return count > 0 ? (
      <div className="pagination-bar muted">
        {count} {label}
      </div>
    ) : null;
  }

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);

  return (
    <div className="pagination-bar">
      <span className="muted">
        {from}–{to} من {count} {label}
      </span>
      <div className="pagination-controls">
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          السابق
        </button>
        <span className="pagination-page">
          صفحة {page} / {totalPages}
        </span>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          التالي
        </button>
      </div>
    </div>
  );
}
