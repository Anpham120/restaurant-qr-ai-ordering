import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = fileURLToPath(new URL("..", import.meta.url));

function read(relativePath: string): string {
  return readFileSync(`${root}/${relativePath}`, "utf8");
}

describe("hub layout audit (no sticky tab scroll gap)", () => {
  it("OpsHubShell keeps hub tabs non-sticky", () => {
    const shell = read("components/operations/OpsHubShell.tsx");
    expect(shell).toContain("const stickyTabs = false");
    expect(shell).not.toMatch(/stickyTabs\s*=\s*true/);
  });

  it("ordering uses one sticky chrome instead of stacked sticky header + nav", () => {
    const layout = read("ordering/OrderingLayout.tsx");
    const css = read("ordering/ordering-layout.css");
    expect(layout).toContain("ordering-chrome");
    expect(css).toContain(".ordering-chrome");
    expect(css).not.toMatch(/\.ordering-nav[\s\S]{0,120}position:\s*sticky/);
    expect(css).not.toMatch(/\.ordering-header[\s\S]{0,120}position:\s*sticky/);
  });

  const hubPages = [
    "pages/admin/OrdersHubPage.tsx",
    "pages/admin/TableHubPage.tsx",
    "pages/admin/MenuHubPage.tsx",
    "pages/counter/CounterHubPage.tsx",
  ];

  it.each(hubPages)("hub page %s does not opt into sticky hub tabs", (pagePath) => {
    const source = read(pagePath);
    expect(source).not.toContain("stickyTabs={true}");
  });

  it("orders hub sends admin table deep links to the scoped table orders page", () => {
    const ordersHub = read("pages/admin/OrdersHubPage.tsx");
    expect(ordersHub).toContain("buildTableOrdersLink(tableFromQuery)");
    const toast = read("components/operations/OpsToastProvider.tsx");
    expect(toast).toContain("buildTableOrdersLink(tableCode)");
  });
});
