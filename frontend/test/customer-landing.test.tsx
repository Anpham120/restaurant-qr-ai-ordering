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

    // Hero renders and a featured dish streams in from the (mocked) menu API.
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect((await screen.findAllByText("Phở bò đặc biệt")).length).toBeGreaterThan(0);

    // Ordering is gated behind a table QR: with no stored table session the
    // primary CTA only shows the "scan QR" notice instead of opening ordering.
    fireEvent.click(screen.getByRole("button", { name: "Quét QR để đặt món" }));

    expect(screen.getByRole("status")).toHaveTextContent(/quét mã QR/i);
    expect(document.body).not.toHaveTextContent(/A05|T05|ORD-1001/);
  });
});
