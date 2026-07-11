import { Link, useLocation } from "react-router-dom";
import { ChevronRight, Sparkles } from "lucide-react";
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
        <Sparkles size={12} />
      </span>
      <span className="customer-ai-launcher-copy">
        <small>Trợ lý món Việt</small>
        <strong>Hỏi AI</strong>
      </span>
      <ChevronRight aria-hidden="true" className="customer-ai-launcher-arrow" size={20} />
    </Link>
  );
}
