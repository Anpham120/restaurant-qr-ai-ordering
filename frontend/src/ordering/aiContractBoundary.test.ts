import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const repoRoot = new URL("../../../", import.meta.url);

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, repoRoot)), "utf8");
}

describe("AI contract boundary (no-touch)", () => {
  it("keeps stable chat API paths in chatService", () => {
    const chatService = read("frontend/src/services/chatService.ts");

    expect(chatService).toContain('"/chat/sessions"');
    expect(chatService).toContain("/messages/stream");
    expect(chatService).toContain("/recommendations");
    expect(chatService).toContain("/feedback");
    expect(chatService).toContain("/assistance");
    expect(chatService).toContain("X-Chat-Session-Token");
  });

  it("keeps AI entry inside ordering-web only", () => {
    const orderingEntry = read("frontend/apps/ordering-web/src/main.tsx");

    expect(orderingEntry).toContain('path: "ai"');
    expect(orderingEntry).toContain("ChatPage");
  });

  it("documents frozen AI directories", () => {
    const manifest = read("docs/ai/AI_NO_TOUCH_BOUNDARY.md");

    expect(manifest).toContain("ai/");
    expect(manifest).toContain("ai-chat-v1.schema.json");
    expect(manifest).toContain("ChatAiProvider.cs");
  });
});
