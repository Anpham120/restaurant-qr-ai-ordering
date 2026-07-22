import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("SessionSmartIndexRedirect", () => {
  const source = readFileSync(
    fileURLToPath(new URL("./SessionSmartIndexRedirect.tsx", import.meta.url)),
    "utf8",
  );

  it("shows loading state while resolving session", () => {
    expect(source).toContain('className="cmc-redirect-page"');
    expect(source).toContain("Đang mở phiên bàn...");
    expect(source).toContain("resolving");
  });

  it("navigates via getSessionResumeDestination when session opens", () => {
    expect(source).toContain("openDineInSession(qrToken, stored.tableCode)");
    expect(source).toContain("getSessionResumeDestination(sessionId, result.session.resumeState, qrToken)");
    expect(source).toContain('navigate(getSessionResumeDestination');
    expect(source).toContain("replace: true");
  });

  it("falls back to menu when qr token or table context is missing", () => {
    expect(source).toContain("!qrToken || stored.sessionId !== sessionId || !stored.tableCode");
    expect(source).toContain('setFallbackPath(`menu');
    expect(source).toContain('<Navigate replace to={fallbackPath} relative="path" />');
  });

  it("does not use location.replace for navigation", () => {
    expect(source).not.toContain("location.replace");
  });
});
