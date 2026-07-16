import { beforeEach, describe, expect, it } from "vitest";
import { authStorage } from "@cmc/auth";
describe("auth storage", () => {
  beforeEach(() => localStorage.clear());
  it("stores and clears the current session", () => {
    const user = { userId: "usr_1", fullName: "Admin", email: "admin@example.com", role: "Admin" as const };
    authStorage.save("token", user);
    expect(authStorage.token()).toBe("token"); expect(authStorage.user()).toEqual(user);
    authStorage.clear(); expect(authStorage.token()).toBeNull();
  });
});
