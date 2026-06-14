import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login, type UserRole } from "../services/authService";
import { PageShell } from "./PageShell";

const roleHome: Record<UserRole, string> = {
  Admin: "/admin",
  Staff: "/staff/orders",
  Kitchen: "/kitchen",
  Customer: "/",
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("staff@example.com");
  const [password, setPassword] = useState("Password123!");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const user = await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from ?? roleHome[user.role] ?? "/", { replace: true });
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Không thể đăng nhập.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title="Đăng nhập vận hành"
      description="Cổng vào dành cho admin, nhân viên phục vụ và bếp. Mỗi màn hình vận hành sẽ kiểm tra role trước khi cho thao tác."
      variant="auth"
    >
      <form className="login-card" onSubmit={handleSubmit}>
        <label>
          Email
          <input
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="staff@example.com"
            type="email"
            value={email}
          />
        </label>
        <label>
          Mật khẩu
          <input
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Nhập mật khẩu"
            type="password"
            value={password}
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="button primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
        </button>
      </form>
    </PageShell>
  );
}
