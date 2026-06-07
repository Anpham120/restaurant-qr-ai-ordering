import { PageShell } from "./PageShell";

export function LoginPage() {
  return (
    <PageShell
      eyebrow="CMC Restaurant"
      title="Đăng nhập vận hành"
      description="Cổng vào dành cho admin, nhân viên phục vụ và bếp trong hệ thống CMC."
      variant="auth"
    >
      <form className="login-card">
        <label>
          Email
          <input placeholder="staff@cmc.local" />
        </label>
        <label>
          Mật khẩu
          <input placeholder="Nhập mật khẩu" type="password" />
        </label>
        <button className="button primary" type="button">
          Đăng nhập
        </button>
      </form>
    </PageShell>
  );
}
