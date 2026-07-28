import { Component, type ErrorInfo, type ReactNode } from "react";

type OpsErrorBoundaryProps = {
  children: ReactNode;
  scope?: string;
};

type OpsErrorBoundaryState = {
  error: Error | null;
};

export class OpsErrorBoundary extends Component<OpsErrorBoundaryProps, OpsErrorBoundaryState> {
  state: OpsErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): OpsErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // #region agent log
    fetch("http://127.0.0.1:7639/ingest/45c610dd-1025-4f92-a068-a057f791be7f", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "613762" },
      body: JSON.stringify({
        sessionId: "613762",
        hypothesisId: "E",
        location: "OpsErrorBoundary.tsx:componentDidCatch",
        message: "ops shell render error",
        data: { scope: this.props.scope ?? "ops", name: error.name, detail: error.message.slice(0, 200), stack: info.componentStack?.slice(0, 300) },
        timestamp: Date.now(),
        runId: "ops-realtime",
      }),
    }).catch(() => {});
    // #endregion
  }

  render() {
    if (this.state.error) {
      return (
        <div className="ops-notice ops-notice--danger" role="alert">
          <strong>Ứng dụng vận hành gặp lỗi hiển thị.</strong>
          <p>Vui lòng tải lại trang. Nếu lỗi lặp lại sau khi khách gọi món, báo quản trị.</p>
        </div>
      );
    }
    return this.props.children;
  }
}
