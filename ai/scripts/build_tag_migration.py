# -*- coding: utf-8 -*-
"""Sinh migration EF cập nhật nhãn thực đơn trong cơ sở dữ liệu, và cập nhật snapshot.

Vì sao cần migration riêng thay vì chỉ sửa `RestaurantMenuSeed.cs`: seed chỉ áp cho cơ
sở dữ liệu **mới tạo**. Cơ sở dữ liệu production đã chạy migration seed từ 07/2026, nên
nó vẫn giữ nhãn cũ cho tới khi có một migration cập nhật.

Hai tệp được sinh:

1. `Migrations/<stamp>_RelabelsMenuTagsWithNamespacedKeys.cs` — cập nhật cột `tags` cho
   91 món bằng SQL thuần, theo tiền lệ `ReconcileLegacyKitchenStatuses` trong repo này
   (thuộc tính `[DbContext]`/`[Migration]` khai ngay trong tệp, không cần tệp Designer).
2. `Migrations/RestaurantDbContextModelSnapshot.cs` — cập nhật mảng `Tags` của 91 món.
   Bắt buộc, vì nhãn được seed qua `HasData` nên EF theo dõi chúng trong snapshot; không
   cập nhật thì lần `dotnet ef migrations add` sau sẽ sinh lại đúng phần khác biệt này.

    python ai/scripts/build_tag_migration.py --check
    python ai/scripts/build_tag_migration.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
MIGRATIONS = (
    REPO_ROOT
    / "backend"
    / "src"
    / "RestaurantQrAiOrdering.Api"
    / "Data"
    / "Migrations"
)
SNAPSHOT_PATH = MIGRATIONS / "RestaurantDbContextModelSnapshot.cs"

# Dấu thời gian cố định, không sinh từ giờ hệ thống: migration phải tái lập được và
# chạy lại script không được tạo ra một migration thứ hai.
STAMP = "20260729120000"
CLASS_NAME = "RelabelsMenuTagsWithNamespacedKeys"
MIGRATION_PATH = MIGRATIONS / f"{STAMP}_{CLASS_NAME}.cs"

HEADER = '''using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RestaurantQrAiOrdering.Api.Data.Migrations;

/// <summary>
/// Gán nhãn lại thực đơn theo khóa có không gian tên, và hợp nhất hai nguồn nhãn.
///
/// Trước migration này, cơ sở dữ liệu và tệp `backend/data/menu-dataset.json` mang hai
/// bộ nhãn khác nhau cho cùng 91 món: cơ sở dữ liệu 1,7 nhãn/món, tệp JSON 15 nhãn/món.
/// Trợ lý AI đọc tệp JSON, còn khách xem thực đơn qua `/api/menu` thấy nhãn từ cơ sở dữ
/// liệu — nên AI suy luận trên dữ liệu dày gấp gần chín lần thứ khách thật nhìn thấy.
///
/// Nhãn cũng đổi dạng: từ tiếng Việt trần (`toi`, `ca`, `nam`) sang khóa có không gian
/// tên (`meal:dinner`, `ingredient:fish`, `ingredient:mushroom`). Dạng cũ trùng với từ
/// thông thường sau khi rút dấu, và đó là gốc của bảy lỗi trong bản AI trước
/// (`cua`/`của`, `chay`/`chạy`, `muc`/`mức`...). Khách không bao giờ gõ `meal:dinner`,
/// nên cả lớp lỗi đó biến mất về mặt cấu trúc.
///
/// Nhãn hiển thị cho khách không đổi: giao diện tra `backend/data/menu-tags.json` và
/// nhận cả khóa mới lẫn tên cũ, nên "Tối", "Cá", "Bình dân" vẫn hiện như trước.
///
/// Sinh bởi `ai/scripts/build_tag_migration.py` — sửa nhãn thì chạy lại script, đừng sửa
/// tay tệp này.
/// </summary>
[DbContext(typeof(RestaurantDbContext))]
[Migration("{stamp}_{cls}")]
public partial class {cls} : Migration
{{
    protected override void Up(MigrationBuilder migrationBuilder)
    {{
        // Cập nhật theo mã món, không theo tên: tên có thể đổi, mã thì không.
        migrationBuilder.Sql(
            """
{up_sql}
            """);
    }}

    protected override void Down(MigrationBuilder migrationBuilder)
    {{
        // Trả về đúng bộ nhãn cũ để có thể lùi lại, kể cả bộ cũ vốn đã thiếu và lệch.
        migrationBuilder.Sql(
            """
{down_sql}
            """);
    }}
}}
'''


def sql_array(tags: list[str]) -> str:
    """Mảng text của PostgreSQL. Nhãn chỉ gồm chữ, số, `_` và `:` nên không có dấu ' —
    vẫn thoát để nếu sau này nhãn có dấu nháy thì không sinh SQL hỏng."""
    inner = ", ".join("'" + t.replace("'", "''") + "'" for t in tags)
    return f"ARRAY[{inner}]::text[]"


def read_old_tags() -> dict[str, list[str]]:
    """Đọc nhãn cũ từ migration seed đã chạy trên production — nguồn duy nhất còn giữ
    trạng thái trước khi gán lại, để `Down()` lùi được."""
    seed = MIGRATIONS / "20260707233442_SeedOfficialMenuAndThirtyTables.cs"
    text = seed.read_text(encoding="utf-8-sig")
    out: dict[str, list[str]] = {}
    # Migration seed dùng hai dạng: `UpdateData` ghi `keyValue: "m_001"`, còn
    # `InsertData` ghi `{ "m_048", ... }`.
    #
    # Phải lấy mảng `new[] {...}` **cuối cùng** trong khối, không phải đầu tiên: dạng
    # `UpdateData` có `columns: new[] { "category_id", ... }` đứng trước
    # `values: new object[] { ..., new[] { <nhãn> } }`. Lấy mảng đầu tiên thì thu về tên
    # cột thay vì nhãn — và với 12 món, `Down()` sẽ ghi "category_id" vào ô nhãn.
    positions = [(m.group(1), m.end()) for m in re.finditer(r'"(m_\d+)"', text)]
    for index, (item_id, end) in enumerate(positions):
        if item_id in out:
            continue
        # Biên là cái nào đến trước: mã món kế tiếp, hoặc `});` kết thúc câu lệnh
        # `migrationBuilder`. Thiếu biên thứ hai thì món cuối của một chuỗi `UpdateData`
        # sẽ trùm sang khối `InsertData` ngay sau nó và thu về danh sách tên cột.
        stop = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        closer = text.find("});", end)
        if closer != -1:
            stop = min(stop, closer)
        arrays = re.findall(r"new\[\]\s*\{([^}]*)\}", text[end:stop])
        if not arrays:
            continue
        out[item_id] = re.findall(r'"([^"]+)"', arrays[-1])
    return out


def build(
    menu: dict, old: dict[str, list[str]], legacy_vocab: set[str]
) -> tuple[str, str, list[str]]:
    problems: list[str] = []
    up, down = [], []
    # Bất biến: mọi nhãn cũ phải nằm trong từ vựng nhãn cũ. Nếu bộ đọc bắt sai khối —
    # ví dụ đọc `columns: new[] { "category_id", ... }` thay vì mảng nhãn — thì lỗi lộ
    # ra ngay đây thay vì đi vào `Down()` của một migration đã chạy trên production.
    for item_id, tags in sorted(old.items()):
        stray = [t for t in tags if t not in legacy_vocab]
        if stray:
            problems.append(
                f"{item_id}: nhãn cũ đọc được không có trong từ vựng nhãn cũ: {stray}"
            )
    for item in menu["items"]:
        item_id = item["id"]
        up.append(
            f"            UPDATE menu_items SET tags = {sql_array(item['tags'])}\n"
            f"                WHERE id = '{item_id}';"
        )
        if item_id not in old:
            problems.append(f"không tìm được nhãn cũ của {item_id} để lùi lại")
            continue
        down.append(
            f"            UPDATE menu_items SET tags = {sql_array(old[item_id])}\n"
            f"                WHERE id = '{item_id}';"
        )
    return "\n".join(up), "\n".join(down), problems


def update_snapshot(menu: dict) -> tuple[int, list[str]]:
    """Đổi mảng `Tags` của từng món trong snapshot, khớp theo `Id = "m_0xx"` ở trên nó."""
    text = SNAPSHOT_PATH.read_text(encoding="utf-8-sig")
    by_id = {m["id"]: m for m in menu["items"]}
    changed = 0
    problems: list[str] = []

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        item = by_id.get(match.group("id"))
        if item is None:
            return match.group(0)
        new_inner = ", ".join(f'"{t}"' for t in item["tags"])
        if match.group("tags").strip() == new_inner:
            return match.group(0)
        changed += 1
        return (
            match.group(0)[: match.start("tags") - match.start()]
            + " "
            + new_inner
            + " "
            + match.group(0)[match.end("tags") - match.start() :]
        )

    pattern = re.compile(
        r'Id = "(?P<id>m_\d+)",(?P<mid>.*?)Tags = new\[\] \{(?P<tags>[^}]*)\}', re.S
    )
    updated, count = pattern.subn(replace, text)
    if count != len(by_id):
        problems.append(
            f"snapshot khớp {count} món nhưng thực đơn có {len(by_id)} — mẫu đọc có thể lạc hậu"
        )
    return changed, problems if problems else [updated]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm, không ghi.")
    args = parser.parse_args(argv)

    menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
    dictionary = json.loads(
        (REPO_ROOT / "backend" / "data" / "menu-tags.json").read_text(encoding="utf-8-sig")
    )
    legacy_vocab = {e["legacy_key"] for e in dictionary["tags"].values()}
    old = read_old_tags()
    up_sql, down_sql, problems = build(menu, old, legacy_vocab)

    print(f"món trong thực đơn        : {len(menu['items'])}")
    print(f"món đọc được nhãn cũ      : {len(old)}")
    print(f"câu UPDATE sinh ra        : {up_sql.count('UPDATE')} lên / {down_sql.count('UPDATE')} lùi")

    snap_text = SNAPSHOT_PATH.read_text(encoding="utf-8-sig")
    changed, snap_result = update_snapshot(menu)
    if snap_result and isinstance(snap_result[0], str) and snap_result[0].startswith("snapshot khớp"):
        problems.extend(snap_result)
        new_snapshot = None
    else:
        new_snapshot = snap_result[0]
    print(f"món đổi nhãn trong snapshot: {changed}")

    if problems:
        print(f"\nVẤN ĐỀ ({len(problems)}):")
        for line in problems:
            print(f"  - {line}")
        return 2

    if args.check:
        print("\n--check: không ghi tệp nào.")
        return 0

    MIGRATION_PATH.write_text(
        HEADER.format(stamp=STAMP, cls=CLASS_NAME, up_sql=up_sql, down_sql=down_sql),
        encoding="utf-8",
    )
    if new_snapshot is not None and new_snapshot != snap_text:
        SNAPSHOT_PATH.write_text(new_snapshot, encoding="utf-8")
    print(f"\nĐã ghi {MIGRATION_PATH.relative_to(REPO_ROOT)}")
    print(f"Đã ghi {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
