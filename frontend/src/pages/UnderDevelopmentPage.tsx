/** Shared “under development” page for features temporarily unavailable in the UI. */
export function UnderDevelopmentPage({
  title,
  description = 'هذه الصفحة قيد التطوير وغير متاحة للاستخدام حالياً.',
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h2>{title}</h2>
          <p className="muted">قيد التطوير</p>
        </div>
      </header>

      <section className="panel feature-disabled" aria-disabled="true">
        <h3>قيد التطوير</h3>
        <p className="muted">{description}</p>
      </section>
    </div>
  );
}
