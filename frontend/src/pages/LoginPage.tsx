import { PageShell } from "./PageShell";

export function LoginPage() {
  return (
    <PageShell
      eyebrow="Auth"
      title="Staff login shell"
      description="Authentication UI placeholder for admin, staff, and kitchen roles."
      variant="auth"
    >
      <form className="login-card">
        <label>
          Email
          <input placeholder="staff@restaurant.local" />
        </label>
        <label>
          Password
          <input placeholder="Password" type="password" />
        </label>
        <button className="button primary" type="button">
          Continue
        </button>
      </form>
    </PageShell>
  );
}
