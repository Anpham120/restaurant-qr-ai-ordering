import { Link, useLocation } from "react-router-dom";
import "./customer-ai-launcher.css";

type CustomerAiLauncherProps = {
  hidden?: boolean;
};

export function CustomerAiLauncher({ hidden = false }: CustomerAiLauncherProps) {
  const location = useLocation();
  const isChatPage = location.pathname === "/chat";

  if (hidden) {
    return null;
  }

  return (
    <Link
      aria-current={isChatPage ? "page" : undefined}
      aria-label="Hỏi AI gợi ý món"
      className="customer-ai-launcher"
      to="/chat"
    >
      <span className="customer-ai-launcher-icon" aria-hidden="true">
        <strong>AI</strong>
        <svg viewBox="0 0 12 12" focusable="false">
          <path d="M6 0c.3 3.8 2.2 5.7 6 6-3.8.3-5.7 2.2-6 6C5.7 8.2 3.8 6.3 0 6 3.8 5.7 5.7 3.8 6 0Z" />
        </svg>
      </span>
      <span className="customer-ai-launcher-copy">
        <small>Trợ lý món Việt</small>
        <strong>Hỏi AI</strong>
      </span>
      <svg className="customer-ai-launcher-arrow" viewBox="0 0 20 20" aria-hidden="true">
        <path d="m7 4 6 6-6 6" />
      </svg>
    </Link>
  );
}
