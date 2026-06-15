import { describe, expect, it } from "vitest";
import { resolveMenuImage } from "../src/utils/menuImages";

describe("resolveMenuImage", () => {
  it("replaces placeholder example.com image URLs with bundled menu assets", () => {
    const imageUrl = resolveMenuImage(
      "Banh flan caramel",
      "https://example.com/images/banh-flan.jpg",
      0,
    );

    expect(imageUrl).toContain("che-khuc-bach");
    expect(imageUrl).not.toContain("example.com");
  });

  it("keeps real user-provided image URLs", () => {
    const imageUrl = resolveMenuImage("Custom dish", "https://cdn.example-cdn.test/custom.webp", 0);

    expect(imageUrl).toBe("https://cdn.example-cdn.test/custom.webp");
  });
});
