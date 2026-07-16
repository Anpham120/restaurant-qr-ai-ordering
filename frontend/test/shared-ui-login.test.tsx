import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, authStorage } from "@cmc/auth";
import { LoginPage } from "@cmc/shared-ui";

afterEach(() => {
  cleanup();
  authStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("shared operations LoginPage", () => {
  it("renders the manual login form without quick role login", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage portalName="CMC Operations" allowedRoles={["Admin", "Staff", "Kitchen"]} />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Đăng Nhập" })).toBeInTheDocument();
    expect(screen.getByLabelText("TÊN ĐĂNG NHẬP")).toBeInTheDocument();
    expect(screen.getByLabelText("MẬT KHẨU")).toBeInTheDocument();
    expect(screen.queryByText("Đăng nhập nhanh")).not.toBeInTheDocument();
    expect(screen.queryByText("Chọn vai trò")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Quản trị viên|Nhân viên|Đầu bếp/i })).not.toBeInTheDocument();
  });

  it("logs in through the backend contract and redirects by role", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            accessToken: "staff-token",
            expiresAt: "2026-06-15T08:00:00Z",
            user: {
              userId: "usr_staff",
              fullName: "Nhan Vien Thu Ngan",
              email: "staff@restaurant.local",
              role: "Staff",
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
            <Route
              path="/login"
              element={
                <LoginPage
                  portalName="CMC Operations"
                  allowedRoles={["Admin", "Staff", "Kitchen"]}
                  roleRedirects={{ Staff: "/staff" }}
                />
              }
            />
            <Route path="/staff" element={<h1>Staff portal</h1>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("TÊN ĐĂNG NHẬP"), {
      target: { value: "staff@restaurant.local" },
    });
    fireEvent.change(screen.getByLabelText("MẬT KHẨU"), {
      target: { value: "Staff@123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Đăng Nhập" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Staff portal" })).toBeInTheDocument();
    });
    expect(authStorage.token()).toBe("staff-token");
  });
});
