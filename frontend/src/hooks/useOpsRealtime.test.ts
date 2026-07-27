import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = fileURLToPath(new URL("..", import.meta.url));

describe("useOpsRealtime polling", () => {
  it("keeps background polling even when SignalR reports connected", () => {
    const source = readFileSync(`${root}/hooks/useOpsRealtime.ts`, "utf8");
    expect(source).not.toContain('connectionStatus === "connected") return');
  });
});
