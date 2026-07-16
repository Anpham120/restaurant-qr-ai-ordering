import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { formatVnd } from "@cmc/brand-ui";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../", import.meta.url);

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, frontendRoot)), "utf8");
}

describe("V43 landing and ordering brand consistency", () => {
  it("loads one shared theme and type system on both hosts", () => {
    const brandCss = read("packages/brand-ui/src/styles.css");
    const landingEntry = read("apps/customer-web/src/main.tsx");
    const orderingEntry = read("apps/ordering-web/src/main.tsx");
    const landingCss = read("src/components/landing/customer-landing.css");
    const orderingCss = read("src/ordering/ordering-layout.css");

    expect(landingEntry).toContain('classList.add("brand-theme")');
    expect(orderingEntry).toContain('classList.add("brand-theme")');
    expect(brandCss).toContain('--brand-font-display: "Playfair Display"');
    expect(brandCss).toContain('--brand-font-body: "Karla"');
    expect(brandCss).toContain('--brand-font-utility: "Manrope"');
    expect(landingCss).toContain("--vian-brown: var(--brand-chestnut)");
    expect(orderingCss).toContain("font-variant-numeric: tabular-nums lining-nums");
  });

  it("formats VND through the shared utility", () => {
    expect(formatVnd(125000)).toBe(new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
      currencyDisplay: "symbol",
      maximumFractionDigits: 0,
    }).format(125000));
  });
});
