/** API-only production probe (no browser). */
const API = "https://api.cmcrestaurant.app/api";
const QR = "qRlg2Bn0D1I6SouZyOQtLyUgZcL6MJTvvLrhufj8eXU";
const SESSION_ID = "ts_4c5284760fab460f8b3b54d62e021594";

async function json(method, path, body, token) {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { "X-Table-Session-Token": token } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let parsed = text;
  try {
    parsed = JSON.parse(text);
  } catch {
    /* keep text */
  }
  return { status: res.status, body: parsed };
}

async function main() {
  const out = { health: null, resolveQr: null, openSession: null, validateOld: null, menu: null, cartAdd: null };

  out.health = await json("GET", "/health");
  out.resolveQr = await json("GET", `/tables/qr/${encodeURIComponent(QR)}`);

  const tableCode =
    typeof out.resolveQr.body === "object" && out.resolveQr.body?.tableCode
      ? out.resolveQr.body.tableCode
      : null;

  if (tableCode) {
    out.openSession = await json("POST", "/table-sessions", { qrToken: QR, tableCode });
  }

  const session = out.openSession?.body;
  const token = session?.sessionToken;
  const sessionId = session?.id ?? SESSION_ID;

  if (token) {
    out.validateOld = await json("GET", `/table-sessions/${encodeURIComponent(SESSION_ID)}`, undefined, token);
    out.menu = await json("GET", "/menu/items?limit=3");
    const firstItem =
      Array.isArray(out.menu.body?.items) && out.menu.body.items[0]?.id
        ? out.menu.body.items[0].id
        : Array.isArray(out.menu.body) && out.menu.body[0]?.id
          ? out.menu.body[0].id
          : null;
    if (firstItem) {
      out.cartAdd = await json(
        "POST",
        `/table-sessions/${encodeURIComponent(sessionId)}/cart/items`,
        { menuItemId: firstItem, delta: 1 },
        token,
      );
      if (out.cartAdd.status >= 400) {
        out.cartAddPatch = await json(
          "PATCH",
          `/table-sessions/${encodeURIComponent(sessionId)}/cart/items`,
          { menuItemId: firstItem, delta: 1 },
          token,
        );
      }
    }
  }

  console.log(JSON.stringify(out, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
