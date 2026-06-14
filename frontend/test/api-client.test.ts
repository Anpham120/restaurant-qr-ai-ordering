import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "@cmc/api-client";
describe("api client", () => {
  afterEach(() => vi.restoreAllMocks());
  it("maps the contract error shape", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "INVALID_CREDENTIALS", message: "No", details: {} } }), { status: 401, headers: { "Content-Type": "application/json" } })));
    await expect(createApiClient({ baseUrl: "https://api.test/api" }).auth.login({ email: "a@b.com", password: "bad" })).rejects.toMatchObject<ApiError>({ status: 401, code: "INVALID_CREDENTIALS" });
  });
  it("adds a bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ userId: "1", fullName: "A", email: "a@b.com", role: "Admin" }), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await createApiClient({ baseUrl: "https://api.test/api", getAccessToken: () => "token" }).auth.me();
    expect((fetchMock.mock.calls[0][1] as RequestInit).headers).toBeInstanceOf(Headers);
    expect(((fetchMock.mock.calls[0][1] as RequestInit).headers as Headers).get("Authorization")).toBe("Bearer token");
  });
});
