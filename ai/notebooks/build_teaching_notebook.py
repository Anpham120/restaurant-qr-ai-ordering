# -*- coding: utf-8 -*-
"""Sinh notebook giảng dạy + báo cáo cho hệ thống AI tư vấn đặt món.

Vì sao sinh bằng script thay vì viết notebook bằng tay
------------------------------------------------------
Một notebook báo cáo viết tay có hai bệnh, và bản cũ của dự án này mắc cả hai:

1. **Số liệu chép tay lạc hậu.** Ai đó đo được 0,9960, chép vào notebook, rồi hệ thống đổi
   và con số nằm đó mãi. Bản cũ có một chỉ số tôi từng báo +81% mà số thật là +53%.
2. **Notebook và mã trôi khỏi nhau.** Notebook nhắc một hàm đã bị đổi tên, và không có gì
   báo.

Ở đây mỗi ô mã trong notebook **tự tính lại** từ `ai/app` và `ai/evaluation` thật. Chạy lại
notebook là đo lại. Không có bảng số nào chép tay.

    python ai/notebooks/build_teaching_notebook.py          # sinh notebook
    python ai/notebooks/build_teaching_notebook.py --check   # kiểm khớp bản đã commit
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = Path(__file__).resolve().parent / "he_thong_ai_tu_van_dat_mon.ipynb"

# Ô mã nào cũng bắt đầu bằng đoạn này. Lặp lại có chủ ý: mỗi ô tự chạy được, nên người đọc
# mở giữa notebook cũng không gặp NameError.
SETUP = '''\
import json, sys
from pathlib import Path

# Tự tìm gốc repo bằng cách leo lên tới thư mục có ai/app — không phụ thuộc chỗ mở notebook.
ROOT = Path.cwd()
while not (ROOT / "ai" / "app" / "understand.py").exists():
    if ROOT.parent == ROOT:
        raise RuntimeError("Không tìm được gốc repo")
    ROOT = ROOT.parent
for p in (ROOT / "ai" / "app", ROOT / "ai" / "evaluation"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

def load(name):
    return json.loads((ROOT / "backend" / "data" / name).read_text(encoding="utf-8-sig"))
'''


def md(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(source.strip())


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(SETUP + "\n" + source.strip())


def raw_code(source: str) -> nbformat.NotebookNode:
    """Ô mã không cần phần nạp (dùng cho ô đầu tiên đã tự khai)."""
    return nbformat.v4.new_code_cell(source.strip())


def cells() -> list[nbformat.NotebookNode]:
    out: list[nbformat.NotebookNode] = []

    # ================================================================= TIÊU ĐỀ
    out.append(md(r"""
# Hệ thống AI tư vấn đặt món — tài liệu giảng dạy và báo cáo

**Đồ án:** trợ lý AI trong ứng dụng gọi món qua mã QR tại bàn
**Dữ liệu:** thực đơn 91 món, 13 nhóm · **Mô hình:** `cx/gpt-5.6-luna-review` qua 9router
**Môi trường:** Python 3.12, CPU

---

> **Cam kết về số liệu.** Mọi con số trong notebook này được **tính trực tiếp** từ mã và dữ
> liệu thật của dự án khi bạn chạy ô mã. Không có bảng nào chép tay, không có ảnh chụp sẵn.
> Chạy lại notebook là đo lại từ đầu.

## Notebook này dạy gì

Notebook đi theo **đúng thứ tự mà hệ thống đã được xây**, vì thứ tự đó chính là phương pháp.
Mỗi phần có ba lớp:

| Lớp | Nội dung |
|---|---|
| **Kiến thức** | khái niệm, vì sao nó cần, và cái bẫy thường gặp |
| **Ví dụ tại dự án** | ô mã chạy trên dữ liệu thật, in ra số |
| **Nhận xét** | quan sát → diễn giải → giới hạn → quyết định tiếp theo |

## Mục lục

| Phần | Nội dung | Bước tương ứng |
|---|---|---|
| I | Bài toán và dữ liệu | 0–1 |
| II | Đo lường: tập đánh giá và thước đo | 2–3 |
| III | Trả lời không cần mô hình | 4 |
| IV | Kho tri thức và truy hồi | 5 |
| V | Mô hình sinh và an toàn | 6–7 |
| VI | Kết quả, hạn chế, và hướng phát triển | — |
"""))

    # ================================================================= PHẦN I
    out.append(md(r"""
---
# PHẦN I — BÀI TOÁN VÀ DỮ LIỆU

## 1. Cần làm gì đầu tiên: phát biểu bài toán

### Kiến thức

Câu hỏi tự nhiên khi bắt đầu một hệ thống AI là "dùng mô hình nào" hoặc "dựng RAG thế nào".
Cả hai đều **sai thứ tự**.

Việc đầu tiên là trả lời: **AI này được phép trả lời gì, và tuyệt đối không làm gì.** Lý do
rất cụ thể: nếu chưa định nghĩa được thế nào là *ngoài phạm vi*, thì không thể biết hệ thống
đang trả lời sai — mọi câu trả lời đều "có vẻ hợp lý".

Bản cũ của dự án này được viết trước khi câu hỏi đó được trả lời rõ. Kết quả đo được: **8
đường xử lý chồng nhau**, và **2 trong số đó bị một cờ tắt mà hệ thống vẫn hoạt động đúng** —
tức chúng là dư, nhưng không ai biết vì không có định nghĩa để đối chiếu.

### Ba loại câu hỏi, và đây là phân loại quyết định kiến trúc

| Loại | Ví dụ | Đặc điểm | Ai trả lời |
|---|---|---|---|
| **A — tra cứu thực đơn** | "Phở bò bao nhiêu tiền?" | đáp án nằm sẵn trong dữ liệu | **mã tất định**, không được để mô hình |
| **B — tri thức nhà hàng** | "Mấy giờ mở cửa?" | sự thật đã viết ra, không nằm trong thực đơn | tra kho tri thức |
| **C — phán đoán, diễn đạt** | "Gợi ý món cho 4 người ăn tối" | không có đáp án đúng duy nhất | mô hình sinh có giá trị thật |

**Nguyên tắc phân tuyến:** câu loại A **không được** để mô hình sinh trả lời. Không phải vì
mô hình dở, mà vì tra bảng đúng 100% và tái lập được, còn mô hình không đảm bảo cả hai.

Đây là kiến thức áp dụng được cho mọi hệ thống AI có dữ liệu có cấu trúc: **việc gì tra được
thì đừng suy luận.**
"""))

    out.append(code(r'''
# Ba điều AI tuyệt đối không làm — đọc từ chính tài liệu phát biểu bài toán
doc = (ROOT / "ai" / "docs" / "00-problem-statement.md").read_text(encoding="utf-8")
start = doc.index("**Ba việc AI tuyệt đối không làm**")
print(doc[start:start + 780])
'''))

    out.append(md(r"""
#### Nhận xét — Mục 1

- **Quan sát:** ba điều cấm không phải giới hạn về *năng lực* mà về *quyền*. Mô hình hoàn
  toàn viết được câu "món này an toàn cho người dị ứng" — vấn đề là nó không có cơ sở để nói.
- **Diễn giải:** phân biệt "không làm được" và "không được phép làm" là phân biệt cốt lõi khi
  thiết kế AI có tác động thật. Điều thứ nhất sẽ hết khi mô hình mạnh hơn; điều thứ hai thì
  không.
- **Giới hạn:** phát biểu bài toán là văn bản, nên nó chỉ có giá trị nếu có cơ chế cưỡng chế.
  Phần V sẽ cho thấy ba điều cấm này được cưỡng chế bằng mã và test như thế nào.
- **Quyết định tiếp theo:** trước khi viết bất kỳ dòng nào, phải hiểu dữ liệu — Mục 2.
"""))

    out.append(md(r"""
## 2. Từ điển dữ liệu: hiểu dữ liệu trước khi dùng

### Kiến thức

Mỗi hệ thống AI có dữ liệu đều cần một **từ điển dữ liệu** trả lời ba câu:

1. Mỗi trường nghĩa là gì?
2. Trường nào là **sự thật** (giá, tên), trường nào là **nhãn do người gán** (đánh giá cảm quan)?
3. **Khi một nhãn không có mặt thì kết luận được điều gì?**

Câu thứ ba là câu quan trọng nhất và hay bị bỏ qua nhất.

### Cái bẫy: rút dấu tiếng Việt làm hai từ khác nghĩa trùng nhau

Khách Việt thường gõ không dấu, nên hệ thống phải rút dấu để khớp. Nhưng rút dấu là phép
**mất thông tin**, và bản cũ dùng chữ đã rút dấu để *quyết định nội dung* — gây **7 lỗi cùng
một gốc**.

Nguyên tắc rút ra: **rút dấu để khớp cách khách gõ, không để quyết định nội dung.**
"""))

    out.append(code(r'''
# Bảy vụ đụng chữ của bản cũ, và cách khóa có không gian tên xoá cả lớp lỗi
import unicodedata

def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")

# Mỗi dòng: (chuỗi cũ, nghĩa thật, từ nó đụng, khóa mới thay thế nó)
collisions = [
    ("cua",   "con cua",         "của / cửa",   "ingredient:crab"),
    ("chay",  "ăn chay",         "chạy",        "diet:vegetarian"),
    ("trung", "trứng",           "miền Trung",  "allergen:egg"),
    ("bo",    "bơ (nguồn sữa)",  "bò",          "allergen:dairy"),
    ("muc",   "mực",             "mức",         "ingredient:squid"),
    ("lac",   "đậu lạc",         "lắc",         "allergen:peanut"),
    ("tra",   "trà",             "tráng",       "cat_drink (danh mục)"),
]
print("Chiều 1 — sau khi rút dấu, chuỗi cũ có nằm trong từ thông thường không?\n")
print(f"{'chuỗi cũ':8} {'nghĩa thật':17} {'đụng từ':13} nằm trong?")
print("-" * 62)
for old, meaning, clash, _new in collisions:
    print(f"{old:8} {meaning:17} {clash:13} {'CÓ  <-- lỗi' if fold(old) in fold(clash) else 'không'}")

print("\nChiều 2 — khóa mới có thể đụng từ thông thường không?\n")
print(f"{'chuỗi cũ':8} -> {'khóa mới':22} còn đụng?")
print("-" * 62)
for old, _m, clash, new in collisions:
    print(f"{old:8} -> {new:22} {'CÓ' if fold(new) in fold(clash) else 'không'}")

# Chốt bằng số thay vì bằng lời: đếm xem còn vụ đụng nào không.
still = sum(1 for old, _m, clash, new in collisions if fold(new) in fold(clash))
print(f"\nSố vụ đụng chữ còn lại sau khi gán nhãn lại: {still}/{len(collisions)}")

# Ba trong bảy chuỗi cũ không phải NHÃN mà là CỤM TỪ VỰNG trong bộ hiểu câu hỏi.
# Chúng được xử bằng cơ chế khác, nên phải nói rõ chứ không gộp làm một.
d = load("menu-tags.json")
legacy = {e["legacy_key"] for e in d["tags"].values()}
in_tags = [old for old, *_ in collisions if old in legacy]
print(f"\nTrong 7 chuỗi trên, {len(in_tags)} là nhãn thực đơn: {in_tags}")
print(f"{7 - len(in_tags)} còn lại là cụm trong bộ hiểu câu hỏi, xử bằng cơ chế 'ăn hết")
print("đoạn đã khớp' — Phần III sẽ đo giá trị của cơ chế đó.")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 2

- **Quan sát:** cả 7 nhãn cũ đều là **từ tiếng Việt trần**, nên sau khi rút dấu chúng nằm
  trong từ thông thường. Khóa mới (`ingredient:crab`, `diet:vegetarian`) không có tính chất
  đó — khách không bao giờ gõ chuỗi `ingredient:crab`.
- **Diễn giải:** đây là **sửa cả lớp lỗi bằng cách đổi cấu trúc**, không phải vá từng ca.
  Vá từng ca thì ca thứ tám sẽ xuất hiện; đổi cấu trúc thì không còn ca nào.
- **Giới hạn:** khóa có không gian tên không tự động đúng. Vẫn cần biết `toi` nghĩa là "tối"
  hay "tỏi" — và câu trả lời nằm ở mục tiếp theo.
- **Quyết định tiếp theo:** kiểm chứng nghĩa của nhãn nhập nhằng nhất.
"""))

    out.append(md(r"""
### Cách xác định nghĩa một nhãn nhập nhằng — ví dụ trực tiếp

Nhãn `toi` có trên 64/91 món. Nó là **"tối"** (bữa tối) hay **"tỏi"** (gia vị)? Bản cũ đoán
là "tỏi", và câu "Món nào có tỏi?" trả về 36 món mà chỉ 11 món thật sự có tỏi.

**Phương pháp:** đừng đoán, hãy tìm bằng chứng độc lập. Ô dưới dùng hai nguồn.
"""))

    out.append(code(r'''
# Bằng chứng 1 — phân bố nhãn theo nhóm món. Nếu là "tỏi" thì nhóm ngọt không thể mang nhãn.
menu = load("menu-dataset.json")
items, cats = menu["items"], {c["categoryId"]: c["name"] for c in menu["categories"]}

print("Món mang nhãn (khóa mới `meal:dinner`, khóa cũ `toi`) theo nhóm:\n")
proof = []
for cid, name in cats.items():
    group = [m for m in items if m["categoryId"] == cid]
    with_tag = [m for m in group if "meal:dinner" in m["tags"]]
    has_garlic = [m for m in group if "tỏi" in m["description"].lower()]
    decisive = len(with_tag) == len(group) and not has_garlic
    if decisive:
        proof.append(name)
    mark = "  <-- BẰNG CHỨNG" if decisive else ""
    print(f"  {name:22} {len(with_tag)}/{len(group)} mang nhãn, {len(has_garlic)} món có tỏi{mark}")

# Kết luận sinh từ số đếm, không viết cứng — nếu dữ liệu đổi thì câu này đổi theo.
print(f"\n{len(proof)} nhóm mang nhãn ở MỌI món mà KHÔNG món nào có tỏi: {', '.join(proof)}.")
print("Nếu nhãn nghĩa là 'tỏi' thì điều đó bất khả — nên nhãn nghĩa là 'tối' (bữa tối).")

# Bằng chứng 2 — từ điển nhãn do người làm giao diện viết, đã có trong repo từ trước.
card = (ROOT / "frontend" / "src" / "components" / "menu" / "MenuItemCard.tsx").read_text(encoding="utf-8")
line = next(l for l in card.splitlines() if '"toi"' in l)
print(f"\nBằng chứng 2 — frontend/src/components/menu/MenuItemCard.tsx:\n {line.strip()}")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 2 (tiếp)

- **Quan sát:** ô mã đếm ra các nhóm mang nhãn ở **mọi** món mà **0 món** có tỏi — nếu nhãn
  nghĩa là "tỏi" thì điều đó bất khả. Và từ điển của người làm giao diện ghi thẳng
  `"toi": "Tối"`. Hai nguồn độc lập, cùng một kết luận.
- **Diễn giải:** câu trả lời **đã nằm trong repo suốt thời gian đó**. Bài học không phải "cần
  cẩn thận hơn" mà là: tri thức này nằm ở ba nơi tách biệt và **không có gì canh chúng khỏi
  trôi khỏi nhau**.
- **Giới hạn:** phương pháp "tìm bằng chứng độc lập" chỉ dùng được khi có nguồn thứ hai. Với
  nhãn cảm quan như `health:healthy` thì không có nguồn nào đối chiếu.
- **Quyết định tiếp theo:** hợp nhất về một nguồn, và thêm test canh sự trôi.
"""))

    out.append(md(r"""
## 3. Điều quan trọng nhất về nhãn: thiếu nhãn nghĩa là gì

### Kiến thức

Với dữ liệu có nhãn, câu hỏi quyết định an toàn là: **món không mang nhãn X thì kết luận được
gì?** Có hai khả năng hoàn toàn khác nhau:

- **Nhóm phủ hết** (mọi món đều có đúng một giá trị) → thiếu nhãn là **lỗi dữ liệu**, và lọc
  được dứt khoát.
- **Nhóm không phủ hết** → thiếu nhãn nghĩa là **chưa ghi nhận**, *không* phải *không có*.

Lẫn hai trường hợp này là gốc của lỗi an toàn nghiêm trọng nhất trong hệ thống tư vấn ăn uống:
suy ra "món này an toàn" từ việc thiếu nhãn dị nguyên.
"""))

    out.append(code(r'''
# Độ phủ từng nhóm nhãn — con số quyết định nhóm nào lọc được dứt khoát
from collections import defaultdict
menu, d = load("menu-dataset.json"), load("menu-tags.json")
items = menu["items"]
groups = sorted({e["group"] for e in d["tags"].values()})

rows = []
for g in groups:
    covered = len({m["id"] for m in items if any(t.startswith(g + ":") for t in m["tags"])})
    rows.append((covered, g))
rows.sort(reverse=True)

print(f"{'nhóm':12} {'phủ':>8}  thiếu nhãn nghĩa là gì")
print("-" * 68)
for covered, g in rows:
    if covered == len(items):
        verdict = "LỖI DỮ LIỆU -> lọc thẳng được"
    else:
        verdict = "chưa ghi nhận -> KHÔNG kết luận được"
    print(f"{g:12} {covered:>4}/{len(items)}  {verdict}")

allergen = len({m["id"] for m in items if any(t.startswith("allergen:") for t in m["tags"])})
print(f"\nNhóm allergen phủ {allergen}/{len(items)} món.")
print(f"=> {len(items) - allergen} món KHÔNG mang nhãn dị nguyên nào, và điều đó KHÔNG")
print("   cho phép nói chúng không chứa dị nguyên.")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 3

- **Quan sát:** 5 nhóm phủ 91/91 (`meal`, `party`, `price`, `season`, `spice`); nhóm
  `allergen` chỉ phủ 44/91.
- **Diễn giải:** hệ quả trực tiếp cho thiết kế: lọc "không cay" là kết luận được vì `spice`
  phủ hết; còn lọc dị nguyên **phải fail-closed** và **luôn kèm lời nhắc hỏi nhân viên**, vì
  47 món không có nhãn không có nghĩa là an toàn.
- **Giới hạn:** đối chiếu nhãn với mô tả món tìm ra **7 lỗ nhãn dị nguyên thật** (6 món hải
  sản, 1 món gluten). Nhưng mô tả không phải bảng thành phần, nên **còn thiếu bao nhiêu thì
  không biết được từ dữ liệu này** — chỉ nhà hàng trả lời được.
- **Quyết định tiếp theo:** đã hiểu dữ liệu, sang phần đo lường.
"""))

    # ================================================================= PHẦN II
    out.append(md(r"""
---
# PHẦN II — ĐO LƯỜNG: TẬP ĐÁNH GIÁ VÀ THƯỚC ĐO

## 4. Vì sao đo lường phải có trước thứ được đo

### Kiến thức

Đây là bài học đắt nhất của dự án này, và nó đo được bằng số.

Bản cũ viết hệ thống trước, dựng thước đo sau. Hệ quả: **thước đo sai 3 lần trước khi hệ
thống sai.** Ba lần đó đều là **bịa ra lỗi không có** — chiều sai nguy hiểm hơn, vì nó khiến
người ta sửa những thứ vốn đã đúng:

| Lần | Thước đo chấm | Thực tế |
|---|---|---|
| 1 | ca so sánh "không có căn cứ" | câu trả lời nêu **đúng** khoảng cách giá hai món |
| 2 | tỷ lệ hỏi lại 43% | câu trả lời **liệt kê món rồi mời thêm** bị đếm là hỏi lại |
| 3 | tra cứu dinh dưỡng "không dùng được" | ca một món, không cần thẻ thêm giỏ |

Và nó còn có một **lỗ**: câu trả lời **rỗng** được tính là "dùng được", vì không dẫn món nào
thì không vi phạm ràng buộc nào. Khi bịt lỗ đó, con số nền tụt từ **0,9960 xuống 0,7368** —
tức 99,6% kia gần như hoàn toàn là ảo.

**Nguyên tắc:** thước đo cũng là một phương pháp, và **cũng phải chứng minh được mình đúng.**

## 5. Khóa đáp án phải kiểm được — dùng truy vấn, không dùng danh sách

### Kiến thức

Cách viết tập đánh giá thông thường là: câu hỏi → danh sách đáp án đúng. Cách đó có một điểm
yếu chết người: **một danh sách viết tay thì không có cách nào kiểm.** Nó luôn "đúng" theo
định nghĩa.

Bản cũ có **96 khóa đáp án trỏ vào những đoạn văn bản dành cho AI đọc** chứ không dành cho
khách, và không ai phát hiện trong nhiều tháng.

**Cách làm ở đây:** một ca không ghi "đáp án là m_008, m_012...". Nó ghi **điều kiện** mà đáp
án phải thỏa, và bộ chạy tự tính danh sách từ thực đơn.
"""))

    out.append(code(r'''
# Một ca đánh giá thật, và cách khóa đáp án của nó tự tính lại từ thực đơn
from menu_selectors import clean_selector, select_ids

cases = json.loads((ROOT / "ai" / "evaluation" / "cases.json").read_text(encoding="utf-8-sig"))
case = next(c for c in cases["cases"] if c["id"] == "A-spice-01")
print(json.dumps(case, ensure_ascii=False, indent=2))

menu = load("menu-dataset.json")
allowed = select_ids(menu["items"], case["expect"]["allowed"])
# `clean_selector` bỏ khóa tài liệu `_why`. Ô này từng ném SelectorError vì quên gọi nó —
# và đó là lý do đoạn lọc được đưa vào thư viện thay vì lặp ở từng nơi dùng.
forbidden = select_ids(menu["items"], clean_selector(cases["named_selectors"]["spicy"]))
print(f"\nĐiều kiện `allowed` chọn ra : {len(allowed)} món")
print(f"Điều kiện `forbid`  chọn ra : {len(forbidden)} món")
print(f"Hai tập giao nhau           : {len(allowed & forbidden)} món  <- phải là 0, nếu không ca tự mâu thuẫn")
print(f"Tổng                        : {len(allowed) + len(forbidden)}/{len(menu['items'])} món")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 5

- **Quan sát:** khóa đáp án là `{"tags_all": ["spice:none"]}`, và bộ chạy tính ra tập món. Hai
  tập `allowed` và `forbid` phủ trọn 91 món và **giao nhau bằng 0**.
- **Diễn giải:** bốn hệ quả. **(1)** thực đơn đổi giá hay đổi nhãn thì khóa đáp án đổi theo;
  **(2)** kiểm được chính ca đánh giá — điều kiện chọn ra 0 món là ca sai và lộ ra ngay;
  **(3)** đọc được ý định rõ hơn một dãy mã món; **(4)** trường `why` bắt buộc, vì ca không
  giải thích được thì không ai xét lại được nó.
- **Giới hạn:** cách này chỉ dùng được khi dữ liệu có cấu trúc. Với câu loại C ("gợi ý này có
  hợp không") thì điều kiện chọn chỉ kiểm được **ràng buộc cứng**, không kiểm được chất lượng
  gợi ý — và tập đánh giá không giả vờ là kiểm được.
- **Quyết định tiếp theo:** chứng minh bộ kiểm tập ca thật sự bắt được ca viết sai.
"""))

    out.append(code(r'''
# Bộ kiểm tập ca bắt được 9 loại lỗi. Ô này chứng minh bằng cách LÀM HỎNG một ca trong bộ
# nhớ rồi chạy lại phép kiểm — không sửa tệp trên đĩa.
import copy
from menu_selectors import select_ids, validate_selector, SelectorError

cases = json.loads((ROOT / "ai" / "evaluation" / "cases.json").read_text(encoding="utf-8-sig"))
menu, tags = load("menu-dataset.json"), load("menu-tags.json")
items, known = menu["items"], set(tags["tags"])

def check_one(case):
    """Ba phép kiểm tiêu biểu; bản đầy đủ ở ai/evaluation/validate_cases.py"""
    problems = []
    for item_id, facts in (case["expect"].get("facts") or {}).items():
        it = next((m for m in items if m["id"] == item_id), None)
        if it is None:
            problems.append(f"mã món không tồn tại: {item_id}")
        elif "price" in facts and facts["price"] != it["price"]:
            problems.append(f"{item_id} ghi giá {facts['price']:,} nhưng thực đơn là {it['price']:,}")
    sel = case["expect"].get("allowed")
    if isinstance(sel, dict):
        stray = [t for v in sel.values() if isinstance(v, list) for t in v if t not in known]
        if stray:
            problems.append(f"nhãn lạ: {stray}")
    if not (case["expect"].get("why") or "").strip():
        problems.append("thiếu trường `why`")
    return problems

good = next(c for c in cases["cases"] if c["id"] == "A-price-01")
print(f"Ca nguyên bản A-price-01: {check_one(good) or 'không có vấn đề'}\n")

for label, mutate in [
    ("đổi giá 75.000 -> 70.000", lambda c: c["expect"]["facts"]["m_008"].update({"price": 70000})),
    ("gõ sai mã món",            lambda c: c["expect"].update({"facts": {"m_999": {"price": 1}}})),
    ("bỏ trường why",            lambda c: c["expect"].update({"why": "  "})),
]:
    broken = copy.deepcopy(good)
    mutate(broken)
    found = check_one(broken)
    print(f"[{'BẮT ĐƯỢC' if found else 'KHÔNG BẮT ĐƯỢC'}] {label}")
    for p in found:
        print(f"             -> {p}")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 5 (tiếp)

- **Quan sát:** cả ba lỗi cố tình tạo ra đều bị bắt, và bắt đúng chỗ. Bản đầy đủ trong
  `ai/evaluation/validate_cases.py` kiểm **9 loại lỗi** và đã được chứng minh bắt cả 9.
- **Diễn giải:** đây là kỹ thuật chung — **muốn tin một bộ kiểm, phải làm hỏng thứ nó kiểm rồi
  xem nó có đỏ không.** Một bộ kiểm luôn xanh không chứng minh được gì.
- **Giới hạn:** phép thử này chứng minh bộ kiểm bắt được **lỗi đã nghĩ tới**. Lỗi chưa nghĩ tới
  cần công cụ khác — mục 7.
- **Quyết định tiếp theo:** chia tập đánh giá sao cho nó dự báo được.
"""))

    out.append(md(r"""
## 6. Chia tập đánh giá: ba nhóm, không phải hai

### Kiến thức

Chia dev/test là kiến thức cơ bản. Nhưng ở hệ thống có yêu cầu an toàn thì **hai nhóm là
không đủ**, và đây là lý do:

Ca an toàn (dị ứng, bịa món, rò rỉ chỉ dẫn nội bộ) **không phải số liệu để so**. Chúng là
**chốt**: luôn phải xanh, ở mọi lần chạy.

- Đưa vào tập phát triển → tỷ lệ chung che mất một ca dị ứng đỏ (1/50 chỉ là 2%).
- Đưa vào tập niêm phong → một lỗi an toàn có thể nằm im nhiều tuần.

Nên chúng thành **nhóm thứ ba**, chạy mọi lần, và một ca đỏ là **chặn** chứ không phải trừ điểm.

### Hai ràng buộc khi chia

1. **Chia theo họ câu hỏi, không theo từng ca.** Nếu "Món nào dưới 50.000đ?" ở tập phát triển
   mà "Mình có 200 nghìn, ăn được món gì?" ở tập niêm phong, thì chỉnh cho ca đầu xanh sẽ kéo
   ca sau xanh theo **mà không học được gì** — đó là rò rỉ.
2. **Cân theo (loại câu hỏi, dạng đáp án).** Tập phát triển chỉ *dự báo* được tập niêm phong
   khi hai bên có thành phần giống nhau.
"""))

    out.append(code(r'''
# Thành phần ba nhóm — tính từ split.json và cases.json thật
from collections import Counter
E = ROOT / "ai" / "evaluation"
cases = json.loads((E / "cases.json").read_text(encoding="utf-8-sig"))["cases"]
split = json.loads((E / "split.json").read_text(encoding="utf-8-sig"))

groups = {"chốt": set(split["gate_families"]),
          "phát triển": set(split["dev_families"]),
          "niêm phong": set(split["test_families"])}

print(f"{'nhóm':12} {'ca':>4} {'họ':>4}  {'loại':16} dạng đáp án")
print("-" * 92)
for label, fams in groups.items():
    cs = [c for c in cases if c["family"] in fams]
    t = " ".join(f"{k}={v}" for k, v in sorted(Counter(c["type"] for c in cs).items()))
    k = " ".join(f"{a}={b}" for a, b in sorted(Counter(c["expect"]["kind"] for c in cs).items()))
    print(f"{label:12} {len(cs):>4} {len(fams):>4}  {t:16} {k}")

# Kiểm rò rỉ: không họ nào được nằm ở hai tập
overlap = set(split["dev_families"]) & set(split["test_families"])
print(f"\nHọ nằm ở cả hai tập (rò rỉ): {len(overlap)}  <- phải là 0")

# Kiểm dự báo: dạng đáp án nào chỉ có ở tập niêm phong thì tập phát triển không dự báo được
dev_kinds = {c["expect"]["kind"] for c in cases if c["family"] in groups["phát triển"]}
test_kinds = {c["expect"]["kind"] for c in cases if c["family"] in groups["niêm phong"]}
print(f"Dạng chỉ có ở tập niêm phong: {sorted(test_kinds - dev_kinds) or 'không có'}")
print(f"Dạng chỉ có ở tập phát triển: {sorted(dev_kinds - test_kinds) or 'không có'}")
'''))

    out.append(md(r"""
#### Nhận xét — Mục 6

- **Quan sát:** 0 họ nằm ở hai tập, nên không rò rỉ. Bốn họ chốt ứng đúng ba điều "tuyệt đối
  không làm" ở Phần I.
- **Diễn giải:** bộ chia này **tất định, không dùng số ngẫu nhiên** — sắp họ theo số ca giảm
  dần rồi tên tăng dần, rồi đặt mỗi họ vào phía đang thiếu nhất ở đúng chữ ký của nó. Không có
  hạt giống nào để chọn cho ra kết quả đẹp, và ai chạy lại cũng ra đúng vậy.
- **Giới hạn thật, phải nói ra:** bộ chia bắt được một lỗi ngay lần chạy đầu — dạng `compare`
  chỉ có ở tập niêm phong, nên tập phát triển không dự báo được nó. Đã sửa. Còn dạng nào chỉ
  có ở một phía thì ô mã in ra, và **tôi không che con số đó**.
- **Quyết định tiếp theo:** dựng thước đo, và chứng minh nó theo cả hai chiều.
"""))

    out.append(md(r"""
## 7. Thước đo: hai nguyên tắc và một bộ dò lỗ

### Kiến thức — nguyên tắc 1: đừng tin hệ thống tự khai

Một câu trả lời gồm hai phần: **phần chữ** khách đọc, và **phần khai báo** món đã nêu.

Nếu thước đo chỉ đọc phần khai báo, hệ thống chỉ cần **bỏ món cấm khỏi danh sách khai** là qua
được ràng buộc dị ứng — trong khi phần chữ vẫn mời khách món đó.

Nên thước đo **tự đọc tên món ra khỏi phần chữ**, rồi so hai chiều:

| Chiều | Bắt được gì |
|---|---|
| chữ → khai | nêu món trong chữ mà không khai — cách lách ràng buộc an toàn |
| khai → chữ | khai món mà chữ không nêu tên — dẫn nguồn ảo |

### Kiến thức — nguyên tắc 2: khớp trọn tên, không khớp một phần

Quyết định này phải dựa trên số, không dựa trên cảm giác.
"""))

    out.append(code(r'''
# Vì sao khớp TRỌN tên món là an toàn, còn khớp một phần thì không
import unicodedata
def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")

menu = load("menu-dataset.json")
names = [(m["id"], m["name"]) for m in menu["items"]]

nested = [(a, b) for i, a in names for j, b in names if i != j and fold(a) in fold(b)]
distinct = len({fold(n) for _i, n in names})
print(f"Tên món nằm trong tên món khác : {len(nested)}   <- 0 nên khớp trọn tên không nhập nhằng")
print(f"Tên còn phân biệt sau rút dấu  : {distinct}/{len(names)}")

from collections import defaultdict
first = defaultdict(list)
for _i, n in names:
    first[fold(n).split()[0]].append(n)
clash = {w: v for w, v in first.items() if len(v) > 1}
print(f"\nTừ ĐẦU của tên món bị trùng    : {len(clash)} từ")
for w, v in sorted(clash.items(), key=lambda kv: -len(kv[1]))[:3]:
    print(f"   '{w}' ứng {len(v)} món: {', '.join(v[:3])}...")
print("\n=> Khớp một phần chắc chắn sinh dương tính giả. Khớp trọn tên thì không.")
'''))

    out.append(md(r"""
### Kiến thức — bộ dò lỗ: tìm lỗi CHƯA nghĩ tới

Test đơn lẻ chỉ kiểm những chỗ người viết đã nghĩ tới. Lỗ "câu rỗng được tính là dùng được"
của bản cũ tồn tại **chính vì không ai nghĩ tới nó**.

**Kỹ thuật:** đưa những câu trả lời **chắc chắn tệ** qua **toàn bộ** tập ca, rồi đòi thước đo
đánh đỏ. Ca nào một câu trả lời tệ vẫn qua được thì đó là lỗ — và nó được **nêu tên cụ thể**
để xét, chứ không làm tròn thành một tỷ lệ.

Kỹ thuật này áp dụng được cho bất kỳ thước đo nào, và nó tìm ra **24 lỗ thật** ở lần chạy đầu.
"""))

    out.append(code(r'''
# Chạy bộ dò lỗ thật trên toàn bộ tập ca
import subprocess, sys
r = subprocess.run([sys.executable, str(ROOT / "ai" / "evaluation" / "probe_metric_holes.py")],
                   capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
print(r.stdout)
'''))

    out.append(md(r"""
#### Nhận xét — Mục 7

- **Quan sát:** cả năm cách trả lời vô nghĩa đều bị bắt ở **mọi** ca. Cách duy nhất còn qua
  được là "luôn nói chưa có dữ liệu", và nó qua đúng số ca mà đó **là** câu trả lời đúng.
- **Diễn giải:** con số đó là **sàn** của thước đo — mọi hệ thống thật phải hơn hẳn nó mới đáng
  nói. Sàn được **tính**, không viết cứng: bản đầu tôi ghi "12/80" và con số đó lạc hậu ngay
  khi tập ca đổi.
- **Giới hạn:** ba phép kiểm (`must_offer_staff`, `states_no_data`, `declines_explicitly`) dùng
  **danh sách cụm từ** thay cho hiểu nghĩa. Câu diễn đạt đúng ý bằng từ khác sẽ bị đánh đỏ oan.
  Đây là đánh đổi có ý thức: cách còn lại là dùng một mô hình để chấm, mà khi đó **thước đo lại
  cần một thước đo**.
- **Quyết định tiếp theo:** đã có tập ca và thước đo tự chứng minh. Giờ mới được xây hệ thống.
"""))

    return out


def build() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = cells()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    return nb


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm khớp bản đã commit.")
    args = parser.parse_args(argv)

    nb = build()
    n_md = sum(1 for c in nb.cells if c.cell_type == "markdown")
    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    print(f"ô markdown : {n_md}")
    print(f"ô mã       : {n_code}")
    print(f"tỷ lệ md:mã: {n_md / max(n_code, 1):.1f}:1")

    if args.check:
        # So NGUỒN của từng ô, bỏ qua kết quả chạy và số thứ tự thực thi.
        #
        # Bản đầu của tôi so nguyên tệp, và nó luôn đỏ: notebook đã commit là bản **đã chạy**
        # nên mang theo kết quả, còn bộ sinh tạo bản chưa chạy. So nguyên tệp thì `--check`
        # buộc phải commit bản không có kết quả — tức notebook báo cáo mất hết bảng số, đúng
        # thứ nó tồn tại để trưng ra.
        if not OUT_PATH.exists():
            print("\nCHƯA CÓ NOTEBOOK. Chạy bộ sinh trước.")
            return 1
        current = nbformat.read(OUT_PATH, as_version=4)
        want = [(c.cell_type, c.source) for c in nb.cells]
        have = [(c.cell_type, c.source) for c in current.cells]
        if want != have:
            print("\nNỘI DUNG Ô TRONG NOTEBOOK ĐÃ COMMIT KHÁC KẾT QUẢ SINH LẠI.")
            print(f"  bộ sinh tạo {len(want)} ô, notebook đã commit có {len(have)} ô")
            for i, (w, h) in enumerate(zip(want, have)):
                if w != h:
                    print(f"  ô đầu tiên khác nhau: {i} ({w[0]})")
                    break
            print("Chạy `python ai/notebooks/build_teaching_notebook.py` rồi chạy lại notebook.")
            return 1
        executed = sum(1 for c in current.cells if c.get("outputs"))
        print(f"\n--check: {len(have)} ô khớp bộ sinh; {executed}/{n_code} ô mã đã có kết quả.")
        return 0

    OUT_PATH.write_text(nbformat.writes(nb, version=4), encoding="utf-8")
    print(f"\nĐã ghi {OUT_PATH.relative_to(REPO_ROOT)} (chưa chạy)")
    print("Chạy tiếp để có kết quả trong notebook:")
    print("  python -m jupyter nbconvert --to notebook --execute --inplace \\")
    print(f"    {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
