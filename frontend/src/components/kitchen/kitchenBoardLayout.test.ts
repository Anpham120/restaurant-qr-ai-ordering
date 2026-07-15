import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = new URL("../../../", import.meta.url);

function read(relativePath: string) {
  return readFileSync(fileURLToPath(new URL(relativePath, frontendRoot)), "utf8");
}

describe("V59 Kitchen board layout", () => {
  it("renders the four operational stages", () => {
    const board = read("src/components/kitchen/KitchenBoard.tsx");

    for (const title of ["Đơn mới", "Đang nấu", "Sẵn sàng", "Đã phục vụ"]) {
      expect(board).toContain(`title="${title}"`);
    }

    expect(board).toMatch(
      /column === "preparing"[\s\S]*?<FinishCookingButton[\s\S]*?onMoveNext=/,
    );
  });

  it("keeps four desktop lanes and responsive tablet/mobile fallbacks", () => {
    const css = read("src/components/operations/operations.css");

    expect(css).toMatch(
      /\.ops-board--kitchen\s*\{[^}]*grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\)/s,
    );
    expect(css).toMatch(
      /@media \(max-width:\s*1100px\)[\s\S]*?\.ops-board--kitchen\s*\{[^}]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/,
    );
    expect(css).toMatch(
      /@media \(max-width:\s*768px\)[\s\S]*?\.ops-board--kitchen\s*\{[^}]*grid-template-columns:\s*1fr/,
    );
  });
});
