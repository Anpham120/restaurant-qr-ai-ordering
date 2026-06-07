import type { ReactNode } from "react";

type PageShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  variant?: "customer" | "admin" | "staff" | "kitchen" | "auth" | "chat";
  stats?: Array<{
    label: string;
    value: string;
    detail: string;
  }>;
  children?: ReactNode;
};

export function PageShell({
  eyebrow,
  title,
  description,
  variant = "customer",
  stats = [],
  children,
}: PageShellProps) {
  return (
    <section className={`page-shell page-shell-${variant}`}>
      <div className="page-heading">
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        <p className="description">{description}</p>
      </div>
      {stats.length > 0 ? (
        <div className="stat-grid" aria-label={`${title} summary`}>
          {stats.map((stat) => (
            <article className="stat-card" key={stat.label}>
              <p>{stat.label}</p>
              <strong>{stat.value}</strong>
              <span>{stat.detail}</span>
            </article>
          ))}
        </div>
      ) : null}
      {children ? <div className="page-body">{children}</div> : null}
    </section>
  );
}
