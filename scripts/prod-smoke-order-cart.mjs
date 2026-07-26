/**
 * Production smoke: ordering menu add-to-cart for a table session URL.
 * Usage: node scripts/prod-smoke-order-cart.mjs "<url>"
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const url =
  process.argv[2] ??
  "https://order.cmcrestaurant.app/table-session/ts_4c5284760fab460f8b3b54d62e021594/menu?qr=qRlg2Bn0D1I6SouZyOQtLyUgZcL6MJTvvLrhufj8eXU";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const result = {
    url,
    sessionReady: false,
    addClicked: false,
    cartDockVisible: false,
    cartItemCount: 0,
    inlineError: "",
    sessionStorage: null,
    apiCartStatus: null,
    apiCartError: null,
  };

  try {
    await page.goto(url, { waitUntil: "networkidle", timeout: 60_000 });
    await page.waitForTimeout(2000);

    result.sessionReady = !(await page.getByText("Phiên gọi món chưa sẵn sàng").isVisible().catch(() => false));
    result.inlineError = (await page.locator(".cmc-inline-error").first().textContent().catch(() => "")) ?? "";

    result.sessionStorage = await page.evaluate(() => {
      const raw = sessionStorage.getItem("cmc-ordering-session-capability-v1");
      if (!raw) return null;
      try {
        const v = JSON.parse(raw);
        return {
          sessionId: v.sessionId,
          tableCode: v.tableCode,
          hasToken: Boolean(v.sessionToken),
          tokenPrefix: v.sessionToken ? String(v.sessionToken).slice(0, 8) : "",
        };
      } catch {
        return { parseError: true };
      }
    });

    const addBtn = page.locator("button.cmc-add-button").first();
    if (await addBtn.isVisible().catch(() => false)) {
      await addBtn.click();
      result.addClicked = true;
      await page.waitForTimeout(2500);
    }

    result.cartDockVisible = await page.locator(".ordering-cart-dock").isVisible().catch(() => false);
    result.inlineError =
      (await page.locator(".cmc-inline-error").first().textContent().catch(() => result.inlineError)) ??
      result.inlineError;

    const cartText = await page.locator(".ordering-cart-dock-count strong").textContent().catch(() => "");
    const m = cartText?.match(/(\d+)/);
    result.cartItemCount = m ? Number(m[1]) : 0;

    if (result.sessionStorage?.sessionId && result.sessionStorage?.hasToken) {
      const api = await page.evaluate(async ({ sessionId }) => {
        const raw = sessionStorage.getItem("cmc-ordering-session-capability-v1");
        const cap = JSON.parse(raw);
        const base = "https://api.cmcrestaurant.app/api";
        const res = await fetch(`${base}/table-sessions/${encodeURIComponent(sessionId)}/cart`, {
          headers: { "X-Table-Session-Token": cap.sessionToken },
        });
        const body = await res.text();
        return { status: res.status, body: body.slice(0, 500) };
      }, { sessionId: result.sessionStorage.sessionId });
      result.apiCartStatus = api.status;
      if (api.status !== 200) result.apiCartError = api.body;
    }

    await page.screenshot({ path: path.join(root, "e2e-screenshots", "prod-smoke-cart.png"), fullPage: true });
  } finally {
    await browser.close();
  }

  console.log(JSON.stringify(result, null, 2));
  process.exit(result.addClicked && (result.cartItemCount > 0 || result.cartDockVisible) ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
