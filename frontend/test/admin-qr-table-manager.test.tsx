import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AdminQrTableManager } from "../src/components/qr/AdminQrTableManager";

vi.mock("qrcode", () => {
  const toDataURL = () => Promise.resolve("data:image/png;base64,QRMOCK");
  return { default: { toDataURL }, toDataURL };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const tableCode = String(input).split("/").pop() ?? "T01";
      return {
        ok: true,
        status: 200,
        json: async () => ({
          tableCode,
          displayName: `Bàn ${tableCode}`,
          isActive: true,
          qrToken: `cmc-table-${tableCode.toLowerCase()}-qr`,
          customerPath: `/table/${tableCode}`,
        }),
      } as Response;
    }),
  );
});

describe("AdminQrTableManager", () => {
  it("renders backend tables grouped by zone", async () => {
    render(<AdminQrTableManager />);

    expect(
      await screen.findByRole("heading", { name: "Sơ đồ bàn đồng bộ với backend" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Khu vực Sảnh chính" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Mở bàn" })).toHaveLength(8);
    expect(screen.getAllByText("Sẵn sàng")).toHaveLength(8);
    expect(await screen.findAllByRole("img", { name: /QR bàn/ })).toHaveLength(8);
    expect(screen.getAllByRole("link", { name: "Tải QR" })).toHaveLength(8);
  });

  it("copies the selected table link and announces success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<AdminQrTableManager />);
    fireEvent.click(await screen.findByRole("button", { name: "Sao chép link bàn T01" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/table/T01`);
    });
    expect(screen.getByRole("status")).toHaveTextContent("Đã sao chép link bàn T01.");
  });
});
