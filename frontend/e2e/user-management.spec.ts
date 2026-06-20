import { expect, test } from "@playwright/test";

const ADMIN_PORTAL = "http://localhost:5174";

const adminUser = {
  userId: "usr_admin",
  fullName: "Quản trị viên",
  email: "admin@restaurant.local",
  role: "Admin",
};

const seededUser = {
  userId: "usr_seed",
  fullName: "Quản trị viên",
  email: "admin@restaurant.local",
  role: "Admin",
  createdAt: "2026-01-01T00:00:00Z",
};

// Inject an authenticated Admin session and stub the auth/me probe so the
// AuthProvider keeps the session instead of clearing it. No backend required.
test.beforeEach(async ({ page }) => {
  await page.addInitScript((user) => {
    window.localStorage.setItem("cmc.accessToken", "e2e-test-token");
    window.localStorage.setItem("cmc.currentUser", user);
  }, JSON.stringify(adminUser));

  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(adminUser) }),
  );
});

test("admin lists and creates operational users", async ({ page }) => {
  await page.route("**/api/users", (route) => {
    if (route.request().method() === "POST") {
      const created = {
        userId: "usr_new",
        fullName: "Nguyễn Văn A",
        email: "staff.new@restaurant.local",
        role: "Staff",
        createdAt: "2026-06-20T00:00:00Z",
      };
      return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(created) });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ users: [seededUser] }),
    });
  });

  await page.goto(`${ADMIN_PORTAL}/users`);

  // Auth injection worked: stayed on the protected route, did not bounce to /login.
  await expect(page).toHaveURL(/\/users$/);
  await expect(page.getByRole("heading", { name: "Quản lý tài khoản" })).toBeVisible();

  // Seeded account from the mocked list renders.
  await expect(page.getByText("admin@restaurant.local").first()).toBeVisible();

  // Create flow: default role is Staff.
  await page.getByLabel("Họ và tên").fill("Nguyễn Văn A");
  await page.getByLabel("Email").fill("staff.new@restaurant.local");
  await page.getByLabel("Mật khẩu", { exact: true }).fill("staffpass123");
  await page.getByRole("button", { name: "Tạo tài khoản" }).click();

  await expect(page.getByText(/Đã tạo tài khoản/)).toBeVisible();
});

test("self-service change-password validates matching confirmation", async ({ page }) => {
  await page.route("**/api/users", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ users: [seededUser] }),
    }),
  );

  await page.goto(`${ADMIN_PORTAL}/users`);
  await expect(page).toHaveURL(/\/users$/);

  // Change-password control lives in the operations sidebar.
  await page.getByRole("button", { name: "Đổi mật khẩu" }).click();
  await page.getByPlaceholder("Mật khẩu hiện tại").fill("Admin@1234");
  await page.getByPlaceholder(/Mật khẩu mới/).fill("newpassword1");
  await page.getByPlaceholder("Xác nhận mật khẩu mới").fill("newpassword2");
  await page.getByRole("button", { name: "Lưu mật khẩu" }).click();

  await expect(page.getByText("Xác nhận mật khẩu không khớp.")).toBeVisible();
});
