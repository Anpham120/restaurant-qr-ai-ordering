import { expect, test } from "@playwright/test";
test("customer landing navigation and sections render", async ({ page }) => {
  await page.goto("http://localhost:5173/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Ẩm thực Việt, gọi món theo cách thông minh hơn");
  await expect(page.getByRole("heading", { name: "Món đặc trưng" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Trải nghiệm liền mạch tại bàn" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cách gọi món" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Chưa biết chọn món gì?" })).toBeVisible();
  await page.getByRole("link", { name: "Hỏi AI", exact: true }).first().click();
  await expect(page).toHaveURL(/\/chat$/);
});
test("customer deep route renders", async ({ page }) => { await page.goto("http://localhost:5173/table/T05"); await expect(page).toHaveURL(/\/table\/T05$/); await expect(page.getByRole("main")).toContainText("T05"); });
for (const [name, port] of [["Admin",5174],["Kitchen",5175],["Staff",5176]] as const) {
  test(`${name} portal protects its root`, async ({ page }) => { await page.goto(`http://localhost:${port}/`); await expect(page).toHaveURL(/\/login$/); await expect(page.getByRole("heading", { name: `${name} Portal` })).toBeVisible(); });
}
