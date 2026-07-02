import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TableEntryPage } from "../src/pages/TableEntryPage";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

function menuResponse() {
  return {
    categories: [
      { categoryId: "cat-main", name: "Món chính" },
      { categoryId: "cat-drink", name: "Đồ uống" },
    ],
    items: [
      {
        id: "mi-1",
        name: "Phở bò đặc biệt",
        description: "Nước dùng bò hầm lâu, thịt bò mềm.",
        price: 95000,
        categoryName: "Món chính",
        imageUrl: "https://example.com/pho.jpg",
        isAvailable: true,
        tags: ["signature"],
      },
      {
        id: "mi-2",
        name: "Trà đào cam sả",
        description: "Trà đào thơm, cam tươi, sả nhẹ.",
        price: 55000,
        categoryName: "Đồ uống",
        imageUrl: "https://example.com/tea.jpg",
        isAvailable: true,
        tags: ["drink"],
      },
    ],
  };
}

function renderTableEntry(qrToken: string) {
  return render(
    <MemoryRouter initialEntries={[`/table/T01?qr=${qrToken}`]}>
      <Routes>
        <Route element={<TableEntryPage />} path="/table/:tableCode" />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

beforeEach(() => {
  window.localStorage.clear();
});

describe("TableEntryPage QR session", () => {
  it("opens a dine-in session and renders menu sections for the scanned table", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/menu")) {
        return jsonResponse(menuResponse());
      }
      if (url.endsWith("/table-sessions")) {
        expect(init?.method).toBe("POST");
        expect(String(init?.body)).toContain("cmc-table-t01-qr");
        return jsonResponse({
          sessionId: "ts_abc",
          orderType: "DineIn",
          status: "Open",
          tableCode: "T01",
          tableDisplayName: "Bàn 01",
          qrToken: "cmc-table-t01-qr",
          customerPath: "/table/T01?qr=cmc-table-t01-qr",
          openedAt: new Date().toISOString(),
          expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
          closedAt: null,
          isExpired: false,
        });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTableEntry("cmc-table-t01-qr");

    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => String(call[0]).endsWith("/table-sessions"))).toBe(
        true,
      );
    });
    await waitFor(() => {
      const context = JSON.parse(window.localStorage.getItem("cmc-restaurant-order-context") ?? "{}");
      expect(context.sessionId).toBe("ts_abc");
      expect(context.tableCode).toBe("T01");
    });

    expect(await screen.findByRole("heading", { name: "Thực đơn bàn T01" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Món chính" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Đồ uống" })).toBeVisible();
    expect(screen.getAllByText("Phở bò đặc biệt").length).toBeGreaterThan(0);
  });

  it("keeps menu visible and shows a re-scan notice when the QR token is invalid", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/menu")) {
        return jsonResponse(menuResponse());
      }
      if (url.endsWith("/table-sessions")) {
        return jsonResponse(
          { error: { code: "QR_NOT_FOUND", message: "QR token does not match an active table.", details: {} } },
          404,
        );
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderTableEntry("bad-token");

    expect(await screen.findByRole("alert")).toHaveTextContent("Mã QR không hợp lệ");
    expect(await screen.findByRole("heading", { name: "Thực đơn bàn T01" })).toBeVisible();
    expect(screen.getAllByText("Phở bò đặc biệt").length).toBeGreaterThan(0);
  });
});
