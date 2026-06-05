type AdminStatePanelProps = {
  title: string;
  description: string;
};

export function AdminStatePanel({ title, description }: AdminStatePanelProps) {
  return (
    <div className="admin-state-panel">
      <strong>{title}</strong>
      <p>{description}</p>
    </div>
  );
}
