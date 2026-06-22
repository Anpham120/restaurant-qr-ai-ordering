import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SuggestedCartActionCard } from "../src/components/chatbot/SuggestedCartActionCard";
import type { SuggestedCartAction } from "../src/types";

afterEach(cleanup);

const action: SuggestedCartAction = {
  menuItemId: "m1",
  name: "Phở bò",
  price: 65000,
  quantity: 2,
  reason: "Món nóng hợp buổi trưa",
  requiresCustomerConfirmation: true,
};

describe("SuggestedCartActionCard", () => {
  it("renders the dish image and confirms inline", () => {
    const onConfirm = vi.fn();
    render(
      <SuggestedCartActionCard
        action={action}
        status="pending"
        imageUrl="https://cdn.example/pho.jpg"
        onConfirm={onConfirm}
        onDismiss={() => {}}
      />,
    );

    expect(screen.getByRole("img", { name: "Phở bò" })).toHaveAttribute(
      "src",
      "https://cdn.example/pho.jpg",
    );

    fireEvent.click(screen.getByRole("button", { name: "Thêm vào giỏ" }));
    expect(onConfirm).toHaveBeenCalledWith(action);
  });

  it("omits the image when none is provided", () => {
    render(
      <SuggestedCartActionCard
        action={action}
        status="pending"
        imageUrl={null}
        onConfirm={() => {}}
        onDismiss={() => {}}
      />,
    );

    expect(screen.queryByRole("img")).toBeNull();
  });

  it("increments quantity and sends the updated amount on confirm", () => {
    const onConfirm = vi.fn();
    render(
      <SuggestedCartActionCard
        action={action}
        status="pending"
        imageUrl={null}
        onConfirm={onConfirm}
        onDismiss={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "+" }));
    fireEvent.click(screen.getByRole("button", { name: "Thêm vào giỏ" }));

    expect(onConfirm).toHaveBeenCalledWith({ ...action, quantity: 3 });
  });

  it("disables ordering when the dish is unavailable", () => {
    render(
      <SuggestedCartActionCard
        action={action}
        status="pending"
        imageUrl={null}
        isAvailable={false}
        onConfirm={() => {}}
        onDismiss={() => {}}
      />,
    );

    expect(screen.getByText("Tạm hết hàng")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Thêm vào giỏ" })).toBeNull();
    expect(screen.getByRole("button", { name: "Bỏ qua" })).toBeInTheDocument();
  });
});
