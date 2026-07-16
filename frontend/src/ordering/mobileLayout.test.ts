import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../", import.meta.url);

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, frontendRoot)), "utf8");
}

describe("V45 mobile customer journeys", () => {
  it("keeps landing navigation reachable at narrow viewports", () => {
    const entry = read("apps/customer-web/src/main.tsx");
    const landingCss = read("src/components/landing/customer-landing.css");
    const i18nCss = read("packages/i18n/src/styles.css");

    expect(entry).toContain('aria-controls="landing-mobile-nav"');
    expect(entry).toContain('landing-nav${menuOpen ? " open" : ""}');
    expect(landingCss).toContain("env(safe-area-inset-top)");
    expect(landingCss).toContain("@media (max-width: 380px)");
    expect(i18nCss).toContain("min-height: 2.75rem");
    expect(i18nCss).toContain("min-width: 2.75rem");
  });

  it("prevents ordering chrome and actions from overflowing 320px", () => {
    const orderingLayout = read("src/ordering/OrderingLayout.tsx");
    const orderingEntryCss = read("apps/ordering-web/src/ordering-app.css");
    const orderingCss = read("src/ordering/ordering-layout.css");
    const menuCss = read("src/components/customer/customer-menu.css");
    const cartCss = read("src/components/customer/customer-cart.css");
    const globalCss = read("src/styles.css");

    expect(orderingEntryCss).toContain(".ordering-entry-top");
    expect(orderingEntryCss).toContain("env(safe-area-inset-top)");
    expect(orderingLayout).toContain('variant="toggle"');
    expect(orderingCss).toContain("overflow-x: clip");
    expect(orderingCss).not.toContain("border-bottom: 2px dashed");
    expect(orderingCss).toContain("@media (max-width: 350px)");
    expect(orderingCss).toContain("min-height: 3.25rem");
    expect(menuCss).toContain("width: 44px");
    expect(menuCss).toContain("@media (max-width: 360px)");
    expect(cartCss).toContain("grid-template-columns: 1fr");
    expect(globalCss).toContain("max-height: 100dvh");
    expect(globalCss).toContain("env(safe-area-inset-bottom)");
  });
});
