import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, authStorage } from "@cmc/auth";
import { LoginPage } from "../src/pages/LoginPage";

afterEach(() => {
  cleanup();
  authStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("LoginPage role routing", () => {
  it("renders only the manual login form", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Đăng nhập hệ thống" })).toBeInTheDocument();
    expect(screen.queryByText("Đăng nhập nhanh")).not.toBeInTheDocument();
    expect(screen.queryByText("Chọn vai trò")).not.toBeInTheDocument();
  });

  it("logs in through the backend contract and redirects kitchen users to the kitchen board", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            accessToken: "kitchen-token",
            expiresAt: "2026-06-14T13:00:00Z",
            user: {
              userId: "usr_kitchen",
              fullName: "Dau Bep",
              email: "kitchen@restaurant.local",
              role: "Kitchen",
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/kitchen" element={<h1>Kitchen board</h1>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "kitchen@restaurant.local" },
    });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Kitchen board" })).toBeInTheDocument();
    });
    expect(authStorage.token()).toBe("kitchen-token");
  });
});
