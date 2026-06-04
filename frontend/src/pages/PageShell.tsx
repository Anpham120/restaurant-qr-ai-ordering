import type { ReactNode } from "react";

type PageShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
};

export function PageShell({
  eyebrow,
  title,
  description,
  children,
}: PageShellProps) {
  return (
    <section className="page-shell">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p className="description">{description}</p>
      {children ? <div className="page-body">{children}</div> : null}
    </section>
  );
}

