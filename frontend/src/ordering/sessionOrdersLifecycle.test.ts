import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("session orders lifecycle", () => {
  it("does not restart the parent session boundary while loading orders", () => {
    const source = readFileSync(
      fileURLToPath(new URL("./SessionOrdersPage.tsx", import.meta.url)),
      "utf8",
    );

    expect(source).not.toContain("await refresh()");
    expect(source).not.toContain("context, refresh");
    expect(source).toContain("getTableSessionOrders(context.sessionId, context.sessionToken)");
  });
});
