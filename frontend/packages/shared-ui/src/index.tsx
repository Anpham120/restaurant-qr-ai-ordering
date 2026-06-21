import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ApiError, createApiClient } from "@cmc/api-client";
import { authStorage, useAuth } from "@cmc/auth";
import type { UserRole } from "@cmc/shared-types";

export function Button({
  children,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  return (
    <button className={`cmc-button cmc-button--${variant}`} {...props}>
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`cmc-card ${className}`}>{children}</section>;
}

export function StatePanel({
  title,
  message,
  kind = "empty",
}: {
  title: string;
  message: string;
  kind?: "empty" | "loading" | "error";
}) {
  return (
    <div className={`cmc-state cmc-state--${kind}`} role={kind === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}) {
  return <span className={`cmc-badge cmc-badge--${tone}`}>{children}</span>;
}

export function NotFoundPage() {
  return (
    <StatePanel
      title="Không tìm thấy trang"
      message="Đường dẫn này không tồn tại trong portal hiện tại."
      kind="error"
    />
  );
}

export function UnauthorizedPage() {
  return (
    <StatePanel
      title="Không có quyền truy cập"
      message="Tài khoản của bạn không có vai trò phù hợp với portal này."
      kind="error"
    />
  );
}

function ChangePasswordControl() {
  const [open, setOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function reset() {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setNote(null);

    if (newPassword.length < 8) {
      setNote({ type: "error", text: "Mật khẩu mới tối thiểu 8 ký tự." });
      return;
    }
    if (newPassword !== confirmPassword) {
      setNote({ type: "error", text: "Xác nhận mật khẩu không khớp." });
      return;
    }

    setBusy(true);
    try {
      const api = createApiClient({ getAccessToken: authStorage.token });
      await api.auth.changePassword({ currentPassword, newPassword });
      reset();
      setOpen(false);
      setNote({ type: "success", text: "Đã đổi mật khẩu." });
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === "CURRENT_PASSWORD_INVALID") {
        setNote({ type: "error", text: "Mật khẩu hiện tại không đúng." });
      } else {
        setNote({ type: "error", text: "Không đổi được mật khẩu. Thử lại sau." });
      }
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="cmc-account-actions">
        {note ? (
          <p className={`cmc-account-note cmc-account-note--${note.type}`} role="status">
            {note.text}
          </p>
        ) : null}
        <button
          type="button"
          className="cmc-account-trigger"
          onClick={() => {
            setNote(null);
            setOpen(true);
          }}
        >
          Đổi mật khẩu
        </button>
      </div>
    );
  }

  return (
    <form className="cmc-account-form" onSubmit={submit}>
      <input
        type="password"
        autoComplete="current-password"
        placeholder="Mật khẩu hiện tại"
        value={currentPassword}
        onChange={(event) => setCurrentPassword(event.target.value)}
      />
      <input
        type="password"
        autoComplete="new-password"
        placeholder="Mật khẩu mới (≥ 8 ký tự)"
        value={newPassword}
        onChange={(event) => setNewPassword(event.target.value)}
      />
      <input
        type="password"
        autoComplete="new-password"
        placeholder="Xác nhận mật khẩu mới"
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
      />
      {note ? (
        <p className={`cmc-account-note cmc-account-note--${note.type}`} role="status">
          {note.text}
        </p>
      ) : null}
      <div className="cmc-account-form-actions">
        <button type="submit" className="cmc-account-trigger" disabled={busy}>
          {busy ? "Đang lưu..." : "Lưu mật khẩu"}
        </button>
        <button
          type="button"
          className="cmc-account-cancel"
          onClick={() => {
            setOpen(false);
            reset();
            setNote(null);
          }}
        >
          Huỷ
        </button>
      </div>
    </form>
  );
}

export type PortalLink = { to: string; label: string };

export function OperationsLayout({
  title,
  subtitle,
  links,
}: {
  title: string;
  subtitle: string;
  links: PortalLink[];
}) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // The sidebar is a fixed off-canvas drawer on small screens; close it whenever
  // the route changes so navigating from inside the drawer dismisses it.
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  // While the mobile drawer is open, let Escape close it and lock body scroll
  // behind the overlay. Desktop never opens the drawer, so this stays inert there.
  useEffect(() => {
    if (!drawerOpen) return;

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setDrawerOpen(false);
    }

    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [drawerOpen]);

  return (
    <div className="cmc-operations-shell">
      <header className="cmc-mobile-topbar">
        <div className="cmc-brand cmc-brand--compact">
          <span className="cmc-brand-mark">CMC</span>
          <strong>{title}</strong>
        </div>
        <button
          type="button"
          className="cmc-nav-toggle"
          aria-label={drawerOpen ? "Đóng menu điều hướng" : "Mở menu điều hướng"}
          aria-expanded={drawerOpen}
          aria-controls="cmc-ops-sidebar"
          onClick={() => setDrawerOpen((open) => !open)}
        >
          <span />
          <span />
          <span />
        </button>
      </header>

      <button
        type="button"
        className={`cmc-drawer-overlay${drawerOpen ? " is-open" : ""}`}
        aria-hidden="true"
        tabIndex={-1}
        onClick={() => setDrawerOpen(false)}
      />

      <aside id="cmc-ops-sidebar" className={`cmc-sidebar${drawerOpen ? " is-open" : ""}`}>
        <div className="cmc-brand">
          <span className="cmc-brand-mark">CMC</span>
          <div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
          </div>
        </div>
        <nav aria-label={`${title} navigation`}>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === "/" || link.to.split("/").length === 2}
              className={({ isActive }) => (isActive ? "cmc-nav-link is-active" : "cmc-nav-link")}
              onClick={() => setDrawerOpen(false)}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="cmc-user">
          <span>{user?.fullName}</span>
          <small>{user?.role}</small>
          <ChangePasswordControl />
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Đăng xuất
          </button>
        </div>
      </aside>
      <main className="cmc-portal-content">
        <Outlet />
      </main>
    </div>
  );
}

export function LoginPage({
  portalName,
  allowedRoles,
  roleRedirects = {},
}: {
  portalName: string;
  allowedRoles: UserRole[];
  roleRedirects?: Partial<Record<UserRole, string>>;
}) {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const target = (location.state as { from?: string } | null)?.from ?? "/";

  function resolveTarget(role: UserRole) {
    if (target !== "/") {
      return target;
    }
    return roleRedirects[role] ?? target;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login({ email, password });
      if (!allowedRoles.includes(user.role)) {
        setError(`Tài khoản ${user.role} không được truy cập ${portalName}.`);
        return;
      }
      navigate(resolveTarget(user.role), { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đăng nhập thất bại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="cmc-login-shell">
      <div className="cmc-login-premium">
        <section className="cmc-form-section">
          <Card className="cmc-login-card">
            <p className="cmc-eyebrow">{portalName}</p>
            <h2>Đăng nhập hệ thống</h2>
            <p>Nhập email và mật khẩu tài khoản vận hành.</p>
            <form onSubmit={submit}>
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="username"
                  placeholder="email@restaurant.local"
                />
              </label>
              <label>
                Mật khẩu
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="Nhập mật khẩu"
                />
              </label>
              {error ? (
                <p className="cmc-form-error" role="alert">
                  {error}
                </p>
              ) : null}
              <Button disabled={busy} type="submit">
                {busy ? "Đang đăng nhập..." : "Đăng nhập"}
              </Button>
            </form>
          </Card>
        </section>
      </div>
    </main>
  );
}

// ===========================================================================
// Form controls
// ===========================================================================
export function Field({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={`cmc-field${error ? " cmc-field--invalid" : ""}`}>
      <label className="cmc-field-label" htmlFor={htmlFor}>
        {label}
        {required ? (
          <span className="cmc-field-req" aria-hidden="true">
            {" *"}
          </span>
        ) : null}
      </label>
      {children}
      {hint && !error ? <p className="cmc-field-hint">{hint}</p> : null}
      {error ? (
        <p className="cmc-field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function Input({
  label,
  hint,
  error,
  id,
  required,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: string;
  error?: string | null;
}) {
  const reactId = useId();
  const inputId = id ?? reactId;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`cmc-field${error ? " cmc-field--invalid" : ""}`}>
      {label ? (
        <label className="cmc-field-label" htmlFor={inputId}>
          {label}
          {required ? (
            <span className="cmc-field-req" aria-hidden="true">
              {" *"}
            </span>
          ) : null}
        </label>
      ) : null}
      <input
        id={inputId}
        className="cmc-input"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        required={required}
        {...props}
      />
      {hint && !error ? (
        <p className="cmc-field-hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="cmc-field-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function Textarea({
  label,
  hint,
  error,
  id,
  required,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label?: string;
  hint?: string;
  error?: string | null;
}) {
  const reactId = useId();
  const fieldId = id ?? reactId;
  const hintId = `${fieldId}-hint`;
  const errorId = `${fieldId}-error`;
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`cmc-field${error ? " cmc-field--invalid" : ""}`}>
      {label ? (
        <label className="cmc-field-label" htmlFor={fieldId}>
          {label}
          {required ? (
            <span className="cmc-field-req" aria-hidden="true">
              {" *"}
            </span>
          ) : null}
        </label>
      ) : null}
      <textarea
        id={fieldId}
        className="cmc-textarea"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        required={required}
        {...props}
      />
      {hint && !error ? (
        <p className="cmc-field-hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="cmc-field-error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function IconButton({
  label,
  children,
  variant = "ghost",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  variant?: "ghost" | "solid" | "danger";
}) {
  return (
    <button
      type="button"
      className={`cmc-icon-button cmc-icon-button--${variant}`}
      aria-label={label}
      title={label}
      {...props}
    >
      {children}
    </button>
  );
}

// ===========================================================================
// Feedback / status
// ===========================================================================
export function Spinner({ size = 24, label = "Đang tải" }: { size?: number; label?: string }) {
  return (
    <span
      className="cmc-spinner"
      role="status"
      aria-live="polite"
      style={{ width: size, height: size }}
    >
      <span className="cmc-spinner-track" />
      <span className="cmc-visually-hidden">{label}</span>
    </span>
  );
}

export function Skeleton({
  width,
  height = 16,
  radius = "var(--radius-sm)",
  className = "",
}: {
  width?: number | string;
  height?: number | string;
  radius?: string;
  className?: string;
}) {
  return (
    <span
      className={`cmc-skeleton anim-shimmer ${className}`.trim()}
      style={{ width: width ?? "100%", height, borderRadius: radius }}
      aria-hidden="true"
    />
  );
}

export function EmptyState({
  icon,
  title,
  message,
  action,
}: {
  icon?: ReactNode;
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="cmc-empty-state">
      {icon ? (
        <div className="cmc-empty-state-icon" aria-hidden="true">
          {icon}
        </div>
      ) : null}
      <strong>{title}</strong>
      {message ? <p>{message}</p> : null}
      {action ? <div className="cmc-empty-state-action">{action}</div> : null}
    </div>
  );
}

export type TimelineItem = {
  label: string;
  sublabel?: string;
  timestamp?: string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
  note?: string;
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="cmc-timeline">
      {items.map((item, index) => (
        <li
          key={index}
          className={`cmc-timeline-item cmc-timeline-item--${item.tone ?? "neutral"}`}
        >
          <span className="cmc-timeline-dot" aria-hidden="true" />
          <div className="cmc-timeline-content">
            <div className="cmc-timeline-row">
              <strong>{item.label}</strong>
              {item.timestamp ? <time className="cmc-timeline-time">{item.timestamp}</time> : null}
            </div>
            {item.sublabel ? <span className="cmc-timeline-sub">{item.sublabel}</span> : null}
            {item.note ? <p className="cmc-timeline-note">{item.note}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ===========================================================================
// Overlays
// ===========================================================================
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  labelledBy,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  labelledBy?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const headingId = labelledBy ?? "cmc-modal-title";

  return createPortal(
    <div
      className="cmc-modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="cmc-modal anim-scale-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? headingId : undefined}
        tabIndex={-1}
        ref={dialogRef}
      >
        {title ? (
          <header className="cmc-modal-header">
            <h2 id={headingId}>{title}</h2>
            <IconButton label="Đóng" onClick={onClose}>
              ×
            </IconButton>
          </header>
        ) : null}
        <div className="cmc-modal-body">{children}</div>
        {footer ? <footer className="cmc-modal-footer">{footer}</footer> : null}
      </div>
    </div>,
    document.body,
  );
}

// ===========================================================================
// Toasts
// ===========================================================================
type ToastTone = "info" | "success" | "warning" | "danger";
type ToastItem = { id: number; tone: ToastTone; message: string };
type ToastContextValue = { toast: (message: string, tone?: ToastTone) => void };

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = "info") => {
      const id = (idRef.current += 1);
      setItems((current) => [...current, { id, tone, message }]);
      window.setTimeout(() => dismiss(id), 4000);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <Toaster items={items} onDismiss={dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a <ToastProvider>");
  }
  return context;
}

export function Toaster({
  items,
  onDismiss,
}: {
  items: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="cmc-toaster" role="region" aria-label="Thông báo" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className={`cmc-toast cmc-toast--${item.tone} anim-toast-in`} role="status">
          <span>{item.message}</span>
          <button
            type="button"
            className="cmc-toast-close"
            aria-label="Đóng thông báo"
            onClick={() => onDismiss(item.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>,
    document.body,
  );
}

// ===========================================================================
// Routing
// ===========================================================================
export function PageTransition({
  children,
  transitionKey,
}: {
  children: ReactNode;
  transitionKey?: string;
}) {
  return (
    <div key={transitionKey} className="cmc-page-transition anim-fade-in-up">
      {children}
    </div>
  );
}
