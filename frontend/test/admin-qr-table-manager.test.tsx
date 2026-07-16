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
  const items = Array.from({ length: 8 }, (_, index) => {
    const tableCode = `T0${index + 1}`;
    const lower = tableCode.toLowerCase();
    return {
      tableCode,
      displayName: `Bàn ${tableCode}`,
      isActive: true,
      qrToken: `cmc-table-${lower}-qr`,
      customerPath: `/table/${tableCode}?qr=cmc-table-${lower}-qr`,
    };
  });

  vi.stubGlobal(
    "fetch",
    vi.fn(async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({ items, total: items.length }),
      } as Response;
    }),
  );
});

describe("AdminQrTableManager", () => {
  it("renders backend tables without fake zone or seat metadata", async () => {
    render(<AdminQrTableManager />);

    expect(await screen.findByRole("heading", { name: "Bàn và mã QR từ backend" })).toBeInTheDocument();
    expect(screen.queryByText("Sức chứa")).not.toBeInTheDocument();
    expect(screen.queryByText("Khu vực")).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Mở trang khách" })).toHaveLength(8);
    expect(screen.getAllByText("Sẵn sàng")).toHaveLength(8);
    expect(await screen.findAllByRole("img", { name: /QR bàn/ })).toHaveLength(8);
    expect(await screen.findAllByRole("link", { name: "Tải QR" })).toHaveLength(8);
  });

  it("copies the selected customer portal link and announces success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<AdminQrTableManager />);
    fireEvent.click(await screen.findByRole("button", { name: "Sao chép link bàn T01" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/table/T01?qr=cmc-table-t01-qr`);
    });
    expect(screen.getByRole("status")).toHaveTextContent("Đã sao chép link bàn T01.");
  });
});
