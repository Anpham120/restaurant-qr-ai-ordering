import { afterEach, describe, expect, it, vi } from "vitest";
import { buildOrderingLink, getOrderingBaseUrl } from "./tableOrderingLink";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("tableOrderingLink", () => {
  it("maps localhost admin ports to ordering port 5177 when env unset", () => {
    vi.stubEnv("VITE_ORDERING_BASE_URL", "");
    expect(
      getOrderingBaseUrl({
        origin: "http://localhost:5174",
        hostname: "localhost",
        protocol: "http:",
        port: "5174",
      }),
    ).toBe("http://localhost:5177");
  });

  it("builds table link against ordering base", () => {
    vi.stubEnv("VITE_ORDERING_BASE_URL", "");
    const link = buildOrderingLink(
      { tableCode: "T01", customerPath: "/table/T01?qr=cmc-table-t01-qr" },
      {
        origin: "http://localhost:5174",
        hostname: "localhost",
        protocol: "http:",
        port: "5174",
      },
    );
    expect(link).toBe("http://localhost:5177/table/T01?qr=cmc-table-t01-qr");
  });

  it("rewrites admin subdomain to order subdomain", () => {
    vi.stubEnv("VITE_ORDERING_BASE_URL", "");
    expect(
      getOrderingBaseUrl({
        origin: "https://admin.cmcrestaurant.app",
        hostname: "admin.cmcrestaurant.app",
        protocol: "https:",
        port: "",
      }),
    ).toBe("https://order.cmcrestaurant.app");
  });
});
