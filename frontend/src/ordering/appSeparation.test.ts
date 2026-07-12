import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../", import.meta.url);

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, frontendRoot)), "utf8");
}

describe("marketing and ordering app separation", () => {
  it("keeps transactional modules out of the marketing entrypoint", () => {
    const marketingEntrypoint = read("apps/customer-web/src/main.tsx");
    const menuPreview = read("src/pages/customer/PublicMenuPreviewPage.tsx");

    expect(marketingEntrypoint).not.toContain("OrderingLayout");
    expect(marketingEntrypoint).not.toContain("CartPage");
    expect(marketingEntrypoint).not.toContain("ChatPage");
    expect(marketingEntrypoint).not.toContain("TableScanPage");
    expect(marketingEntrypoint).not.toContain('to="/#cach-dat-mon"');
    expect(marketingEntrypoint).not.toContain("Đặt món tại bàn");
    expect(marketingEntrypoint).toContain("OrderingHostRedirect");
    expect(menuPreview).not.toContain("customerMenuStorage");
    expect(menuPreview).not.toContain("loadMenuCart");
    expect(menuPreview).not.toContain("saveMenuCart");
  });

  it("keeps marketing modules out and owns AI inside the ordering entrypoint", () => {
    const orderingEntrypoint = read("apps/ordering-web/src/main.tsx");
    const orderingMenu = read("src/ordering/OrderingMenuPage.tsx");

    expect(orderingEntrypoint).not.toContain("CustomerHomePage");
    expect(orderingEntrypoint).not.toContain("RestaurantAlbumPage");
    expect(orderingEntrypoint).toContain("ChatPage");
    expect(orderingEntrypoint).toContain('path: "ai"');
    expect(orderingEntrypoint).toContain("OrderingLayout");
    expect(orderingMenu).not.toContain("CustomerTestimonials");
    expect(orderingMenu).not.toContain("CustomerWhyChooseUs");
  });

  it("routes each domain to its own artifact without cross-app public assets", () => {
    const nginxConfig = read("nginx.conf");
    const marketingViteConfig = read("apps/customer-web/vite.config.ts");
    const orderingViteConfig = read("apps/ordering-web/vite.config.ts");

    expect(nginxConfig).toContain("cmcrestaurant.app /usr/share/nginx/html/customer;");
    expect(nginxConfig).toContain("order.cmcrestaurant.app /usr/share/nginx/html/ordering;");
    expect(nginxConfig).toContain("customer.cmcrestaurant.app /usr/share/nginx/html/ordering;");
    expect(nginxConfig).toContain("root $cmc_app_root;");
    expect(nginxConfig).toContain("try_files $uri $uri/ /index.html;");
    expect(marketingViteConfig).toContain('publicDir: "../../public"');
    expect(orderingViteConfig).toContain('publicDir: "../../public"');
    expect(orderingViteConfig).not.toContain("customer-web/public");
  });

  it("generates table QR links on the ordering domain", () => {
    const qrManager = read("src/components/qr/AdminQrTableManager.tsx");

    expect(qrManager).toContain("VITE_ORDERING_BASE_URL");
    expect(qrManager).toContain("https://order.cmcrestaurant.app");
    expect(qrManager).not.toContain("VITE_CUSTOMER_BASE_URL");
    expect(qrManager).not.toContain("https://customer.cmcrestaurant.app");
  });
});
