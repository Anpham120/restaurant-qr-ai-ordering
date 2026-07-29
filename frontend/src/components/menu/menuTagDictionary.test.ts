import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { localizeMenuTag } from "@cmc/i18n/menu";

import { tagLabel } from "./MenuItemCard";

/**
 * Canh sự đồng bộ giữa từ điển nhãn thực đơn và hai bảng nhãn ở frontend.
 *
 * Vì sao cần: tri thức "nhãn nào nghĩa là gì" từng nằm ở ba nơi tách biệt — bảng
 * tiếng Việt trong MenuItemCard, bảng tiếng Anh trong i18n, và phần suy đoán trong
 * dịch vụ AI. Ba bản trôi khỏi nhau mà không có gì báo:
 *
 *   - AI đoán nhãn `toi` là "tỏi" trong khi giao diện hiển thị đúng "Tối", nên câu
 *     "Món nào có tỏi?" trả về 36 món ăn buổi tối.
 *   - Bảng tiếng Anh chỉ phủ 54/80 nhãn, nên khách xem bằng tiếng Anh thấy khóa thô
 *     ("toi", "trua", "khong cay") ở 30 nhãn, và 4 mục trỏ vào nhãn đã bị bỏ.
 *
 * Cả hai lỗi đều là trôi dữ liệu, không phải lỗi logic — nên chỗ chặn đúng là một
 * test đọc từ điển gốc và so, chứ không phải đọc kỹ hơn khi sửa tay.
 */

const frontendRoot = new URL("../../../", import.meta.url);
const dictionaryPath = fileURLToPath(
  new URL("../backend/data/menu-tags.json", frontendRoot),
);
const menuPath = fileURLToPath(
  new URL("../backend/data/menu-dataset.json", frontendRoot),
);

type TagEntry = {
  group: string;
  value: string;
  label_vi: string;
  label_en: string;
  legacy_key: string;
  exclusive: boolean;
};

const dictionary = JSON.parse(readFileSync(dictionaryPath, "utf8")) as {
  groups: string[];
  exclusive_groups: string[];
  tags: Record<string, TagEntry>;
};
const entries = Object.entries(dictionary.tags);

describe("từ điển nhãn thực đơn", () => {
  it("phủ mọi nhãn trong thực đơn, không sót nhãn nào", () => {
    const menu = JSON.parse(readFileSync(menuPath, "utf8")) as {
      items: { id: string; tags: string[] }[];
    };
    const used = new Set(menu.items.flatMap((item) => item.tags));
    expect(used.size).toBeGreaterThan(0);
    for (const tag of used) {
      expect(dictionary.tags[tag], `nhãn dùng trong thực đơn nhưng thiếu trong từ điển: ${tag}`)
        .toBeDefined();
    }
  });

  it("hiển thị nhãn tiếng Việt cho mọi khóa, không rơi về chữ thô", () => {
    for (const [key, entry] of entries) {
      expect(tagLabel(key), key).toBe(entry.label_vi);
    }
  });

  it("hiển thị nhãn tiếng Anh cho mọi khóa, không rơi về chữ thô", () => {
    for (const [key, entry] of entries) {
      expect(localizeMenuTag(key, "en", entry.label_vi), key).toBe(entry.label_en);
    }
  });

  it("vẫn hiển thị đúng tên nhãn cũ mà /api/menu còn trả về", () => {
    // Cơ sở dữ liệu chưa được gán nhãn lại, nên nhãn cũ vẫn đến từ API. Bỏ nhánh
    // này là khách thấy "binh dan" thay cho "Bình dân".
    for (const [key, entry] of entries) {
      expect(tagLabel(entry.legacy_key), `${entry.legacy_key} (cũ của ${key})`)
        .toBe(entry.label_vi);
      expect(localizeMenuTag(entry.legacy_key, "en", entry.label_vi), entry.legacy_key)
        .toBe(entry.label_en);
    }
  });

  it("nhãn không xác định thì trả về nguyên văn, không ném lỗi", () => {
    // Chiều ngược lại: test trên sẽ vẫn xanh nếu tagLabel trả về mọi thứ được
    // truyền vào. Ca này chứng minh nó thật sự tra bảng.
    expect(tagLabel("nhan-khong-ton-tai")).toBe("nhan-khong-ton-tai");
    expect(localizeMenuTag("nhan-khong-ton-tai", "en", "Dự phòng")).toBe(
      "nhan-khong-ton-tai",
    );
  });

  it("khóa có không gian tên, nên không thể trùng từ thường trong câu hỏi", () => {
    // Đây là lý do tồn tại của lần gán nhãn lại. Bản cũ có 14 nhãn trùng từ thường
    // tiếng Việt sau khi rút dấu (`toi`↔tôi/tỏi, `cua`↔của/cửa, `chay`↔chạy...),
    // và 3 nhãn có token nằm trong nhãn khác (`nam` trong `quanh nam`, `mien Nam`).
    for (const [key, entry] of entries) {
      expect(key, key).toBe(`${entry.group}:${entry.value}`);
      expect(dictionary.groups, `nhóm lạ: ${entry.group}`).toContain(entry.group);
      expect(key, `khóa phải không có dấu cách: ${key}`).not.toMatch(/\s/);
    }
    // Không khóa nào là tiền tố/hậu tố của khóa khác — điều mà nhãn cũ vi phạm.
    const keys = entries.map(([key]) => key);
    for (const key of keys) {
      const nested = keys.filter((other) => other !== key && other.includes(key));
      expect(nested, `khóa ${key} nằm trong khóa khác: ${nested.join(", ")}`).toEqual([]);
    }
  });

  it("nhóm loại trừ nhau thì mỗi món chỉ mang một giá trị", () => {
    const menu = JSON.parse(readFileSync(menuPath, "utf8")) as {
      items: { id: string; name: string; tags: string[] }[];
    };
    for (const group of dictionary.exclusive_groups) {
      for (const item of menu.items) {
        const values = item.tags.filter((tag) => tag.startsWith(`${group}:`));
        expect(
          values.length,
          `${item.name} mang ${values.length} giá trị của nhóm ${group}: ${values.join(", ")}`,
        ).toBeLessThanOrEqual(1);
      }
    }
  });
});
