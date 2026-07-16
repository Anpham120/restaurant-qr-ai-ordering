import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { CustomerAiLauncher } from "../src/components/customer/CustomerAiLauncher";

afterEach(cleanup);

describe("CustomerAiLauncher", () => {
  it("links every customer page to the AI assistant", () => {
    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <CustomerAiLauncher />
      </MemoryRouter>,
    );

    const launcher = screen.getByRole("link", { name: "Hỏi AI gợi ý món" });
    expect(launcher).toHaveAttribute("href", "/chat");
  });

  it("exposes the current state on the chat page", () => {
    render(
      <MemoryRouter initialEntries={["/chat"]}>
        <CustomerAiLauncher />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Hỏi AI gợi ý món" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
