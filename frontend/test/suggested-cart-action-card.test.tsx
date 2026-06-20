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

    fireEvent.click(screen.getByRole("button", { name: "Xác nhận thêm vào giỏ" }));
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
});
