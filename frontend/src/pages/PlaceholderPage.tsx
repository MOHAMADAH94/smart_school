export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="page">
      <header className="page-header">
        <h2>{title}</h2>
        <p className="muted">سيتم تفعيل هذه الصفحة في المراحل القادمة.</p>
      </header>
    </div>
  );
}
