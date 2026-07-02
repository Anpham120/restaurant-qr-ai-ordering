import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CustomerHomePage } from "../src/pages/CustomerHomePage";

describe("CustomerHomePage", () => {
  it("renders a restaurant landing page and requires QR only when ordering", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          categories: [{ categoryId: "cat-1", name: "Món chính" }],
          items: [
            {
              id: "mi-1",
              name: "Phở bò đặc biệt",
              description: "Nước dùng bò hầm lâu, thịt bò mềm.",
              price: 95000,
              categoryName: "Món chính",
              imageUrl: "",
              isAvailable: true,
              tags: ["signature"],
            },
          ],
        }),
      })),
    );

    render(
      <MemoryRouter>
        <CustomerHomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("CMC Restaurant");
    expect(screen.getByRole("link", { name: "Xem món nổi bật" })).toBeVisible();
    expect(await screen.findByText("Phở bò đặc biệt")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "Đặt món tại bàn" }));

    expect(screen.getByRole("status")).toHaveTextContent("vui lòng quét mã QR");
    expect(screen.queryByRole("link", { name: /Hỏi AI/i })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/A05|T05|ORD-1001/);
  });
});
