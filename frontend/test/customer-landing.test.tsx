import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CustomerHomePage } from "../src/pages/CustomerHomePage";

describe("CustomerHomePage", () => {
  it("renders the QR-only entry screen without direct menu access", () => {
    render(
      <MemoryRouter>
        <CustomerHomePage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("CMC Restaurant");
    expect(screen.getByText(/Vui lòng quét mã QR được đặt tại bàn/i)).toBeVisible();
    expect(screen.getByText("Chờ quét QR tại bàn")).toBeVisible();
    expect(screen.queryByRole("link", { name: /Xem thực đơn/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Hỏi AI/i })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/A05|T05|ORD-1001/);
  });
});
