import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), "utf8");
}

describe("ordering experience", () => {
  it("keeps the selected cart summary visible while browsing the menu", () => {
    const menu = read("./OrderingMenuPage.tsx");
    const styles = read("../components/customer/customer-menu.css");

    expect(menu).toContain("ordering-cart-dock");
    expect(menu).toContain("summary.count");
    expect(menu).toContain("summary.total");
    expect(styles).toContain("position: fixed");
  });

  it("keeps quick prompts inside chat and lets the backend resolve the table", () => {
    const chat = read("../pages/chatbot/ChatbotPage.tsx");

    expect(chat).toContain("cmc-chat-quick-prompts-inline");
    expect(chat).not.toContain("cmc-chat-side-panel");
    expect(chat).toContain("tableSessionId: orderContext.sessionId");
    expect(chat).not.toContain("tableCode: orderContext.tableCode");
    expect(chat).not.toContain("content,\n        tableCode");
  });
});
