import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AdminQrTableManager } from "../src/components/qr/AdminQrTableManager";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AdminQrTableManager", () => {
  it("renders zones, table links, and current status counts", () => {
    render(<AdminQrTableManager />);

    expect(screen.getByRole("heading", { name: "Sơ đồ bàn cho một ca phục vụ liền mạch" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Khu vực Sảnh chính" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Mở bàn/ })).toHaveLength(6);
    expect(screen.getAllByText("Đang phục vụ")).toHaveLength(3);
  });

  it("copies the selected table link and announces success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<AdminQrTableManager />);
    fireEvent.click(screen.getByRole("button", { name: "Sao chép link bàn T-01" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/table/T-01`);
    });
    expect(screen.getByRole("status")).toHaveTextContent("Đã sao chép link bàn T-01.");
  });
});
