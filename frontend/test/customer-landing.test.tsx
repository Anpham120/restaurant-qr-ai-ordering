import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CustomerHomePage } from "../src/pages/CustomerHomePage";

describe("CustomerHomePage", () => {
  it("renders public landing actions and sections without a fake table context", () => {
    render(<MemoryRouter><CustomerHomePage /></MemoryRouter>);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Ẩm thực Việt, gọi món theo cách thông minh hơn",
    );
    expect(screen.getAllByRole("link", { name: /Xem thực đơn/i })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /Xem thực đơn/i })[0]).toHaveAttribute("href", "/menu");
    expect(screen.getByRole("heading", { name: "Món đặc trưng" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Trải nghiệm liền mạch tại bàn" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Cách gọi món" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Chưa biết chọn món gì?" })).toBeVisible();
    expect(document.body).not.toHaveTextContent(/A05|T05|ORD-1001/);
  });
});
