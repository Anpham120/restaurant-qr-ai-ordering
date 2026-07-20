import { useEffect } from "react";
import { createRoot } from "react-dom/client";

function LegacyHostRedirect({ targetPath }: { targetPath: string }) {
  useEffect(() => {
    const adminBase = import.meta.env.VITE_OPS_BASE_URL
      ?? (typeof window !== "undefined" && window.location.hostname.startsWith("staff.")
        ? window.location.href.replace(/^staff\./, "admin.")
        : window.location.origin.replace("5176", "5174"));
    window.location.replace(new URL(targetPath, adminBase).toString());
  }, [targetPath]);
  return <main><p>Đang chuyển sang ứng dụng vận hành…</p></main>;
}

createRoot(document.getElementById("root")!).render(<LegacyHostRedirect targetPath="/counter" />);
