// Designed empty state: shown whenever a data artifact is absent.
// We never invent a number to fill a gap.
export default function Pending({
  title = "Not available yet",
  children,
}: {
  title?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="ca-pending" role="status">
      <span className="ca-chip">
        <span className="ca-dot ca-dot--warn" />
        {title}
      </span>
      {children && <div style={{ maxWidth: 480 }}>{children}</div>}
    </div>
  );
}
