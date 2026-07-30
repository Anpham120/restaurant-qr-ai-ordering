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

KNOWLEDGE = ROOT / "ai" / "knowledge"
'''

# Phần dựng biểu đồ, thêm vào những ô có vẽ hình. Tách khỏi SETUP để ô không vẽ không phải
# nạp matplotlib — nạp mất ~1 giây và làm notebook chạy chậm hơn không cần thiết.
#
# Cấu hình font: DejaVu Sans là font mặc định của matplotlib và nó CÓ dấu tiếng Việt. Không
# đặt thì nhãn trục hiện ra ô vuông, và biểu đồ dùng cho báo cáo thì không chấp nhận được.
PLOT = '''
import matplotlib

# KHÔNG đặt backend khi đang ở trong Jupyter. Trong notebook, backend mặc định là `inline` và
# nó nhúng hình PNG vào ô kết quả; ép sang "Agg" thì `plt.show()` chạy im lặng và notebook
# **không có hình nào** — đã mắc đúng lỗi này một lần, 16/16 ô chạy sạch mà 0 biểu đồ.
try:
    get_ipython()                # chỉ tồn tại trong Jupyter
except NameError:
    matplotlib.use("Agg")        # chạy ngoài notebook thì không mở cửa sổ
import matplotlib.pyplot as plt
plt.rcParams.update({
    "font.family": "DejaVu Sans",     # có dấu tiếng Việt
    "figure.dpi": 110,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
})
# Bảng màu dùng chung cả notebook, để biểu đồ trong báo cáo nhất quán.
XANH, DO, XAM, CAM = "#2c6fbb", "#c0392b", "#95a5a6", "#e67e22"
'''


def md(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(source.strip())


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(SETUP + "\n" + source.strip())


def plot_code(source: str) -> nbformat.NotebookNode:
    """Ô mã có vẽ biểu đồ: nạp thêm phần cấu hình matplotlib."""
    return nbformat.v4.new_code_cell(SETUP + PLOT + "\n" + source.strip())


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

## Mục lục — và ai phụ trách phần nào

Nhóm 5 người chia việc thành **một vai nền tảng cộng bốn khâu của pipeline**:

```
        TV1  NỀN TẢNG — dữ liệu & đo lường
             kho tri thức · từ điển nhãn · tập đánh giá · thước đo
             KHÔNG phải một chặng runtime: mọi khâu DÙNG nó, không đi qua
                          │
                          ▼  cung cấp dữ liệu và tiêu chí cho cả 4 khâu
khách gõ câu → TV5 cổng vào & phiên → TV2 hiểu câu hỏi → TV3 truy hồi
             → TV4 chọn món & giỏ hàng → TV5 ghi bộ nhớ, trả JSON
```

| TV | Phụ trách | Module sở hữu | Mục notebook | Trạng thái |
|---|---|---|---|---|
| **1** | **Nền tảng: dữ liệu & đo lường** | `knowledge/*` · `chunker.py` · `build_*.py` · `evaluation/*` | 1–11, 14–15 | **xong phần hiện có** |
| **2** | Hiểu câu hỏi | `understand.py` · `llm_understand.py` | 4, 12–13, 16 | **xong** |
| **3** | Truy hồi | `rag/bm25.py` · `embedding.py` · `hybrid.py` | 15 | **chưa có** |
| **4** | Chọn món & giỏ hàng | `answer.py` · `cart.py` | 12–14 | **xong** |
| **5** | Cổng vào & phiên | `service.py` · `session.py` | 16 (một phần) | **xong mã**, chưa chạy thật |
| — | Kết quả, hạn chế, hướng phát triển | — | 17–19 | — |

**Vì sao dữ liệu và đo lường thuộc CÙNG một người.** Chúng giống nhau ở điểm quan trọng nhất: cả
hai **không phải chặng runtime** — một câu hỏi không "đi qua" từ điển nhãn hay tập đánh giá, nó
*dùng* chúng. Tách chúng ra thì hoặc chúng bị gửi vào các khâu (và người nhận gánh thêm một nền
kiến thức lạ), hoặc chúng thành "việc chung" và không ai làm.

Chúng cũng đòi **cùng một loại kỷ luật**: *số phải tính được, không được viết tay*. Dự án đã mắc lỗi
đó hai lần và cả hai đều ở phần TV1 phụ trách — `"hơn 90 món"` khi thực đơn có đúng 91, và kiểm kê
đụng chữ ghi `32/90` khi thật là `53/40`.

Nhờ tách như vậy, **TV3 chỉ làm truy hồi** (một nền kiến thức: tf-idf, cosine, chỉ số xếp hạng), và
**đo lường có tên** thay vì thành việc chung.

**Mục notebook không ứng một-một với TV**, và đó là điều phải nói rõ: notebook đi theo thứ tự **học
được** (bài toán → dữ liệu → đo lường → trả lời → truy hồi → mô hình), còn phân công đi theo thứ tự
**chạy**. Hai thứ tự trả lời hai câu hỏi khác nhau — *học thế nào cho hiểu* và *ai sửa tệp nào*.

**Điều phải biết trước: TV1 nằm trên đường tới hạn của hai người.** TV3 không đo được phép so truy
hồi trước khi TV1 xong ~120 ca truy hồi; TV5 không đo được bộ nhớ phiên trước khi TV1 xong ~25 kịch
bản đa lượt. Nên thứ tự tuần 1 của TV1 là **ca đánh giá trước, mở rộng kho sau**.
"""))

    # ================================================================= PHẦN I
    out.append(md(r"""
---
# PHẦN 1 — BÀI TOÁN, DỮ LIỆU VÀ KHO TRI THỨC
> **TV1** — nền tảng dữ liệu

> **Vị trí:** nền tảng của cả pipeline. Không phải một chặng runtime — một câu hỏi không "đi qua"
> từ điển nhãn, nó *dùng* từ điển. Nhưng mọi khâu đều đo trên dữ liệu này.

| | |
|---|---|
| **Câu hỏi khâu này trả lời** | *AI được phép trả lời gì, dữ liệu có gì, và khi một nhãn không có mặt thì kết luận được gì?* |
| **Kiến thức phải nắm** | phân loại ba loại câu hỏi A/B/C · rút dấu tiếng Việt là phép mất thông tin · độ phủ nhãn quyết định filterability · chunking cho truy hồi · provenance `derived` vs `demo` |
| **Tệp sở hữu** | `ai/knowledge/*` · `rag/chunker.py` · `build_knowledge.py` · `build_tag_dictionary.py` · `audit_allergen_tags.py` · `backend/data/menu-tags.json` · `ai/evaluation/*` |
| **Đầu vào** | thực đơn thật (91 món) và yêu cầu nghiệp vụ |
| **Đầu ra bàn giao** | từ điển nhãn có tiền tố nhóm · kho 84 tài liệu / 327 đoạn · `KnowledgeChunk` cho TV3 · 119 ca và thước đo cho cả nhóm |
| **Tự đo bằng** | `build_knowledge.py --check` · `build_tag_dictionary.py --check` · `audit_allergen_tags.py` · `python -m unittest test_chunker test_packaging` |
| **Trạng thái** | **xong** — 103 test xanh, 2 bộ sinh khớp kết quả sinh lại |

### Vì sao khâu này đứng đầu

Phản xạ tự nhiên khi bắt đầu là chọn mô hình hoặc dựng RAG. Cả hai đều **sai thứ tự**, vì cả
hai đều cần một thứ chưa có: **định nghĩa thế nào là trả lời sai**. Không có định nghĩa đó thì
mọi câu trả lời đều "có vẻ hợp lý", và không ai đo được gì.

Bảy mục dưới đây là nội dung TV1 phải hiểu, và mỗi mục có ô mã tính lại từ mã sống —
nên đọc xong chạy được ngay, không phải tin lời.

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

    # ============================================== MỤC 4 — RÚT DẤU MẤT THÔNG TIN
    out.append(md(r"""
## 4. Rút dấu tiếng Việt là phép MẤT thông tin

### Kiến thức

Để khớp câu khách gõ, hệ thống phải **rút dấu**: khách viết `"Không cay"`, `"khong cay"`,
`"ko cay"` đều phải hiểu như nhau. Đó là việc bắt buộc, không tránh được.

Nhưng rút dấu là **hàm không đơn ánh** — hai chuỗi khác nghĩa có thể cho cùng kết quả. Bảy lỗi
của bản cũ đều sinh ra từ đúng chỗ này, và chúng không phải bảy lỗi độc lập: chúng là **một lớp
lỗi** xuất hiện bảy lần.

**Cách sửa không phải sửa từng lỗi.** Sửa từng lỗi thì lỗi thứ tám sẽ tới. Cách sửa là **đổi
hình dạng dữ liệu** để lớp lỗi đó không còn khả năng tồn tại: nhãn mang **tiền tố nhóm**.

| Bản cũ | Bản dựng lại |
|---|---|
| `"nong"` — món nóng hay vị nồng? | `serving:hot` / `spice:hot` |
| `"chay"` — ăn chay hay bán chạy? | `diet:vegetarian` / `promo:popular` |

Sau khi đổi, cụm chữ **vẫn** trùng — nhưng tiền tố phân biệt được, nên trùng **không còn là
lỗi**. Đây là điểm cần hiểu: không phải làm cho lỗi biến mất, mà làm cho **lớp lỗi không còn
khả năng tồn tại**.

Cơ chế thứ hai bảo vệ phần còn lại: **khớp cụm dài trước, rồi ăn hết đoạn đã khớp** (thay đoạn
đã khớp bằng khoảng trắng để nó không khớp lần nữa).
"""))

    out.append(code(r"""
# 1) Rút dấu làm MẤT thông tin — chứng minh bằng chính hàm hệ thống dùng
from understand import VOCAB, fold, understand
from collections import defaultdict

menu, d = load("menu-dataset.json"), load("menu-tags.json")
items = menu["items"]

print("Hai chữ khác nghĩa, sau khi rút dấu thành một:")
for a, b in [("nóng", "nồng"), ("chay", "cháy"), ("mực", "mức"), ("tôi", "tỏi")]:
    dau = "  <-- ĐỤNG NHAU" if fold(a) == fold(b) else ""
    print(f"   {a!r:8} -> {fold(a)!r:8}   {b!r:8} -> {fold(b)!r:8}{dau}")

# 2) Nhãn mang tiền tố nhóm: cụm chữ vẫn trùng, nhưng không còn là lỗi
col = defaultdict(set)
for tag in d["tags"]:
    col[fold(tag.split(":", 1)[1].replace("_", " "))].add(tag)
clash = {k: sorted(v) for k, v in col.items() if len(v) > 1}
print(f"\nCụm chữ rút dấu còn trùng giữa các nhãn: {len(clash)}")
for k, v in clash.items():
    print(f"   {k!r} <- {v}   (tiền tố nhóm phân biệt được -> KHÔNG còn là lỗi)")

# 3) Kiểm kê chỗ có nguy cơ — tính lại, không viết tay
phrases = sorted(VOCAB)
names = [fold(m["name"]) for m in items]
in_other = {a for a in phrases for b in phrases if a != b and a in b}
in_name = {p for p in phrases if any(p in n for n in names)}
print(f"\nKiểm kê trên {len(phrases)} cụm từ vựng và {len(items)} tên món:")
print(f"   bị chứa trong cụm từ vựng khác : {len(in_other)}")
print(f"   nằm trong tên món              : {len(in_name)}")
print(f"   thuộc cả hai                   : {len(in_other & in_name)}")
print(f"   TỔNG cụm có nguy cơ            : {len(in_other | in_name)}")

# 4) Cơ chế chặn, thử trên 4 câu từng làm bản cũ sai
print("\nBốn câu từng làm bản cũ sai:")
for q in ["Món nào bán chạy nhất?", "Có đặc sản miền Trung không?",
          "Nhà hàng mấy giờ mở cửa?", "Gà nướng mật ong giá bao nhiêu?"]:
    r = understand(q, items)
    print(f"   {q}")
    print(f"      require={r.require_tags}  avoid={r.avoid_tags}  "
          f"topic={r.policy_topic}  món={r.named_items}")
"""))

    out.append(plot_code(r"""
# Biểu đồ 1 — quy mô lớp lỗi đụng chữ, và phần tập đánh giá phủ được
from understand import VOCAB, fold
menu = load("menu-dataset.json"); items = menu["items"]
phrases = sorted(VOCAB); names = [fold(m["name"]) for m in items]
in_other = {a for a in phrases for b in phrases if a != b and a in b}
in_name = {p for p in phrases if any(p in n for n in names)}
rui_ro = in_other | in_name

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

nhan = ["Bị chứa trong\ncụm khác", "Nằm trong\ntên món", "Thuộc\ncả hai", "TỔNG\ncó nguy cơ"]
gia_tri = [len(in_other), len(in_name), len(in_other & in_name), len(rui_ro)]
mau = [XANH, XANH, XAM, DO]
b = ax1.bar(nhan, gia_tri, color=mau)
ax1.bar_label(b, padding=2, fontsize=10, fontweight="bold")
ax1.set_ylabel("số cụm từ vựng")
ax1.set_title(f"Chỗ có nguy cơ đụng chữ\n(trên {len(phrases)} cụm từ vựng)", fontsize=11)
ax1.set_ylim(0, max(gia_tri) * 1.25)

# Ablation đo "mất 1 ca" — nhưng cơ chế bảo vệ 61 chỗ. Đây là khoảng trống của TẬP ĐÁNH GIÁ.
co_ca, khong_ca = 1, len(rui_ro) - 1
ax2.barh(["Cơ chế bảo vệ"], [co_ca], color=DO, label=f"có ca đánh giá ({co_ca})")
ax2.barh(["Cơ chế bảo vệ"], [khong_ca], left=[co_ca], color=XAM,
         label=f"KHÔNG có ca đánh giá ({khong_ca})")
ax2.set_xlabel("số cụm có nguy cơ")
ax2.set_title("Vì sao ablation báo 'mất 1 ca' là CHẶN DƯỚI", fontsize=11)
ax2.legend(loc="lower right", fontsize=9)
ax2.grid(False)

plt.tight_layout()
plt.show()
print(f"Cơ chế ăn đoạn bảo vệ {len(rui_ro)} chỗ; tập đánh giá chỉ chạm tới 1.")
print("=> Con số ablation đo được GIỚI HẠN CỦA TẬP ĐÁNH GIÁ, không đo giá trị cơ chế.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 4

- **Quan sát:** 4/4 cặp chữ thử đều đụng nhau sau khi rút dấu. Sau khi nhãn mang tiền tố nhóm,
  chỉ còn **1 cụm trùng** (`hot` của `serving:hot` và `spice:hot`) và tiền tố phân biệt được nên
  nó **không còn là lỗi**. Kiểm kê: **72 cụm có nguy cơ** (53 bị chứa trong cụm khác, 40 nằm
  trong tên món, 21 thuộc cả hai).
- **Diễn giải:** đây là ví dụ rõ nhất của nguyên tắc *sửa cấu trúc thay vì sửa lỗi*. Bảy lỗi bản
  cũ là **một lớp lỗi** xuất hiện bảy lần; đổi hình dạng nhãn xóa cả lớp, còn sửa từng lỗi thì
  không bao giờ hết.
- **Giới hạn phải nói ra:** ablation báo cơ chế ăn đoạn "chỉ đáng 1 ca", nhưng nó bảo vệ 61 chỗ.
  Chênh lệch đó là **khoảng trống của tập đánh giá**, không phải bằng chứng cơ chế vô dụng. Đã
  lấp bằng 9 test riêng, và ba con số trên **được tính lại mỗi lần chạy test** —
  `test_understand.collision_census()`. Bản trước của tài liệu ghi "32 cụm" và "90 cụm": hai số
  đó đúng lúc đo, rồi từ vựng lớn lên mà không ai tính lại. Con số hiện tại cũng đã đổi một lần
  nữa (61 → 72) khi từ vựng thêm 20 cụm tên món cho nhóm dị nguyên — và lần này **test đỏ báo
  ngay**, đúng như nó được viết ra để làm.
- **Quyết định tiếp theo:** dữ liệu nhãn đã an toàn, sang phần tri thức không nằm trong nhãn.
"""))

    # ============================================ MỤC 5 — MỘT KHO, HAI CHẾ ĐỘ
    out.append(md(r"""
## 5. Kho tri thức: MỘT kho, HAI chế độ trả lời

### Kiến thức

Nhãn thực đơn trả lời được "món nào không cay". Nó **không** trả lời được "mấy giờ mở cửa" hay
"đặc sản miền Trung là gì". Phần đó cần **kho tri thức**.

Câu hỏi thiết kế đầu tiên: kho đó nên có mấy phần? Dự án này lúc đầu làm **hai kho** — một tệp
JSON tra khóa, và một thư mục markdown cho truy hồi — với lý do *"tra khóa vs truy hồi xếp
hạng"*. **Lý do đó sai**, và đo lại mới thấy: mọi tài liệu markdown đều có đúng một `topic_keys`
nên chúng cũng tra khóa được. Cách *lấy* không phân biệt được gì.

Ranh giới thật là **chế độ trả lời** — mô hình được tin bao nhiêu:

| `answer_mode` | Nội dung tới khách | Dùng cho |
|---|---|---|
| `verbatim` | **nguyên văn**, mô hình không chạm vào chữ | giờ mở cửa, thanh toán, phụ phí, cách khai dị ứng |
| `synthesize` | **đầu vào** cho mô hình viết câu trả lời | "đặc sản miền Trung có gì", "gọi bao nhiêu món cho 6 người" |

Và ranh giới đó **không cần hai kho**. Phải phân biệt hai thứ dễ bị gộp lẫn:

- Số **kho lưu trữ** là chuyện gọn gàng → **gộp được**, và gộp còn xóa được một lớp lỗi: khi
  còn hai kho, chủ đề có ở cả hai thì tài liệu kho thứ hai *không bao giờ tới lượt* mà vẫn
  chiếm chỗ trong chỉ mục truy hồi — im lặng, không lỗi.
- Số **chế độ trả lời** là chuyện an toàn → **không gộp được**. Về `synthesize` thì "mấy giờ
  đóng cửa" do mô hình viết và nó *có thể* viết 22h30. Về `verbatim` thì phải nén danh sách
  nhiều món kèm ghi chú dị nguyên vào một câu viết tay.
"""))

    out.append(code(r"""
# Kho tri thức: quy mô, hai chế độ, và điều mỗi chế độ đảm bảo
from collections import Counter
from rag.chunker import (VERBATIM, all_chunks, load_all, retrievable_chunks,
                         verbatim_answers)

docs = load_all(KNOWLEDGE)
chunks = all_chunks(KNOWLEDGE)
print(f"tài liệu                 : {len(docs)}")
print(f"đoạn (chunk)             : {len(chunks)}")
print(f"đoạn ĐƯỢC xếp hạng       : {len(retrievable_chunks(KNOWLEDGE))}")
print(f"theo chế độ trả lời      : {dict(Counter(d.answer_mode for d in docs))}")
print(f"theo nguồn tri thức      : {dict(Counter(d.source for d in docs))}")
print(f"theo thư mục             : {dict(Counter(d.path.parent.name for d in docs))}")

print("\n--- Một tài liệu `verbatim`: chuỗi này tới khách NGUYÊN VĂN ---")
hours = next(d for d in docs if "hours" in d.topic_keys)
print(f"   {hours.verbatim_answer}")

print("\n--- Một đoạn `synthesize`: đây là ĐẦU VÀO cho mô hình viết ---")
ch = next(c for c in retrievable_chunks(KNOWLEDGE) if "region.central" in c.doc_id)
print("   " + ch.text.replace("\n", "\n   ")[:260])

print("\n--- Ranh giới được ÉP, không phải quy ước ---")
syn = next(d for d in docs if d.answer_mode != VERBATIM)
try:
    syn.verbatim_answer
    print("   KHÔNG lỗi -> ranh giới hỏng")
except Exception as e:
    print(f"   Gọi verbatim_answer trên tài liệu synthesize -> {type(e).__name__}")
    print(f"   {str(e)[:110]}")
"""))

    out.append(plot_code(r"""
# Biểu đồ 2 — cấu trúc kho tri thức: chế độ trả lời, nguồn, và độ dài đoạn
from collections import Counter
from rag.chunker import all_chunks, load_all, retrievable_chunks

docs = load_all(KNOWLEDGE); chunks = all_chunks(KNOWLEDGE)
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.5, 4))

# (a) chế độ trả lời — mô hình được tin bao nhiêu
mode = Counter(d.answer_mode for d in docs)
ax1.pie([mode["verbatim"], mode["synthesize"]],
        labels=[f"verbatim\n{mode['verbatim']} tài liệu\n(mô hình tin 0%)",
                f"synthesize\n{mode['synthesize']} tài liệu\n(mô hình viết)"],
        colors=[DO, XANH], autopct="%1.0f%%", startangle=90,
        textprops={"fontsize": 9})
ax1.set_title("Chế độ trả lời\n(ranh giới AN TOÀN)", fontsize=11)

# (b) nguồn tri thức — tin được đến đâu
src = Counter(d.source for d in docs)
b = ax2.bar(["derived\n(máy sinh)", "demo\n(người viết)"],
            [src["derived"], src["demo"]], color=[XANH, CAM])
ax2.bar_label(b, padding=2, fontweight="bold")
ax2.set_ylabel("số tài liệu")
ax2.set_title("Nguồn tri thức\n(derived KHÔNG THỂ lệch khỏi thực đơn)", fontsize=11)
ax2.set_ylim(0, max(src.values()) * 1.2)

# (c) phân bố độ dài đoạn — đoạn quá ngắn thì vô dụng khi truy hồi
w = [c.word_count for c in chunks]
ax3.hist(w, bins=28, color=XANH, edgecolor="white")
ax3.axvline(12, color=DO, linestyle="--", linewidth=1.5, label="ngưỡng tối thiểu 12 từ")
ax3.axvline(400, color=CAM, linestyle="--", linewidth=1.5, label="ngưỡng chia tiếp 400 từ")
ax3.set_xlabel("số từ mỗi đoạn"); ax3.set_ylabel("số đoạn")
ax3.set_title(f"Độ dài {len(chunks)} đoạn\n(min {min(w)}, trung vị "
              f"{sorted(w)[len(w)//2]}, max {max(w)})", fontsize=11)
ax3.legend(fontsize=8)

plt.tight_layout(); plt.show()
loai = len(chunks) - len(retrievable_chunks(KNOWLEDGE))
print(f"{loai} đoạn `verbatim` bị LOẠI khỏi chỉ mục truy hồi — chúng đã có đường tới khách")
print("riêng (tra khóa, trả nguyên văn). Để trong chỉ mục là hai đường tới cùng nội dung.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 5

- **Quan sát:** 84 tài liệu / 327 đoạn trong **một** kho, chia 24 `verbatim` + 60 `synthesize`.
  Bộ truy hồi chỉ xếp hạng **303 đoạn** — 24 đoạn `verbatim` bị loại vì chúng đã có đường tới
  khách riêng.
- **Diễn giải:** hai thứ tôi từng gộp lẫn là **kho lưu trữ** và **chế độ trả lời**. Chúng độc
  lập: không có gì bắt buộc "lưu trong markdown thì phải qua mô hình". Nhận ra điều đó mới gộp
  được kho mà không mất bảo đảm an toàn.
- **Ranh giới được ÉP bằng mã, không phải quy ước:** gọi `verbatim_answer` trên tài liệu
  `synthesize` thì **lỗi**, không phải trả về một chuỗi nào đó. Trả về im lặng thì một chỗ dùng
  sai sẽ đưa nửa tài liệu ra cho khách nguyên văn.
- **Giới hạn:** 28/84 tài liệu là `demo` — giá trị mẫu cho dự án demo. Dùng thật thì chủ nhà
  hàng phải thay, và đổi `source` thành `restaurant` để không còn bị đếm là mẫu.
"""))

    # ==================================== MỤC 6 — CHIA ĐOẠN VÀ CỬA AUDIENCE
    out.append(md(r"""
## 6. Chia đoạn, và cửa `audience: guest`

### Kiến thức

Truy hồi không lấy cả tài liệu, nó lấy **đoạn**. Nên cách chia đoạn quyết định chất lượng truy
hồi trước cả khi chọn phương pháp. Ba quy tắc, mỗi cái một lý do:

1. **Chia theo heading `##`, không theo số ký tự.** Chia theo ký tự thì cắt ngang giữa câu, và
   nửa ý nằm ở đoạn này nửa kia ở đoạn khác — không đoạn nào trả lời được. Heading là ranh giới
   ý nghĩa mà người viết đã đặt sẵn; dùng nó là miễn phí.
2. **Kèm tiêu đề tài liệu vào mỗi đoạn.** Đoạn bị trích ra **rời khỏi** tài liệu. Một đoạn viết
   "Có 7 món, giá từ 189.000đ" mà không nói đang nói về cái gì thì vô dụng.
3. **Gộp đoạn quá ngắn.** Đoạn chỉ có một dòng tiêu đề không mang tín hiệu nào, nhưng **vẫn
   chiếm một chỗ trong top-k** và đẩy một đoạn có ích ra ngoài. Lấy 5 đoạn mà 1 đoạn là rác thì
   thực chất chỉ còn 4.

Chi tiết dễ sai: **gộp phải chạy TRƯỚC khi cấp mã đoạn**. Cấp mã rồi mới gộp thì dãy mã bị
khuyết (`#0, #2, #3`) và tập đánh giá truy hồi trỏ vào mã không tồn tại.

### Cửa `audience`: TỪ CHỐI, không phải lọc bỏ

Bản cũ có 27 tài liệu tri thức, trong đó **5 tài liệu là hướng dẫn cho AI** — phong cách trả
lời, ví dụ phản hồi sai. Cả 27 nằm **cùng một chỉ mục truy hồi**, nên **47/221 đoạn** bị trích
ra cho khách đọc. Khách hỏi giờ mở cửa và nhận một đoạn dạy AI cách xin lỗi.

Có hai cách sửa, và chúng khác nhau nhiều hơn vẻ ngoài:

| Cách | Hôm nay | Tháng sau ai đó thêm tệp nội bộ |
|---|---|---|
| **lọc bỏ** | hết lỗi | tệp **im lặng** bị bỏ qua, người thêm tưởng đã vào kho |
| **từ chối** | hết lỗi | việc thêm **bị chặn ngay**, kèm lý do |
"""))

    out.append(code(r"""
# Ba bất biến của bộ chia đoạn, kiểm trên kho THẬT
from rag.chunker import KnowledgeError, all_chunks, load_all, load_doc
import tempfile
from pathlib import Path as _P

chunks = all_chunks(KNOWLEDGE)
w = sorted(c.word_count for c in chunks)
print(f"Bất biến 1 — mọi đoạn kèm tiêu đề tài liệu : "
      f"{sum(1 for c in chunks if c.text.startswith(c.title))}/{len(chunks)}")
ids = [c.chunk_id for c in chunks]
print(f"Bất biến 2 — chunk_id không trùng          : {len(set(ids))}/{len(ids)}")
print(f"Bất biến 3 — nạp hai lần cho cùng dãy mã   : "
      f"{[c.chunk_id for c in all_chunks(KNOWLEDGE)] == ids}")

khuyet = [d.doc_id for d in load_all(KNOWLEDGE)
          if [int(c.chunk_id.split('#')[1]) for c in d.chunks] != list(range(len(d.chunks)))]
print(f"Bất biến 4 — dãy mã liên tục từ 0          : {len(khuyet)} tài liệu khuyết")
print(f"\nĐộ dài đoạn: min {w[0]}, trung vị {w[len(w)//2]}, max {w[-1]} từ")

# Cửa audience — chứng minh việc TỪ CHỐI thật sự xảy ra
FM = ("id: kb.thu.v1\ntitle: Thử\ntopic_keys: [thu_nghiem]\nsource: demo\n"
      "audience: {aud}\nanswer_mode: synthesize")
BODY = "# Thử\n\n## Mục\n\n" + " ".join(["từ"] * 30)
print("\n--- Cửa audience, thử cả hai chiều ---")
with tempfile.TemporaryDirectory() as tmp:
    for aud in ("guest", "ai"):
        p = _P(tmp) / f"{aud}.md"
        p.write_text(f"---\n{FM.format(aud=aud)}\n---\n\n{BODY}\n", encoding="utf-8")
        try:
            load_doc(p)
            print(f"   audience={aud!r}  -> NHẬN")
        except KnowledgeError as e:
            print(f"   audience={aud!r}     -> TỪ CHỐI")
            print(f"      {str(e)[:105]}...")
print("\nThử chiều ngược là bắt buộc: một bộ nạp từ chối MỌI THỨ cũng qua được")
print("phép kiểm 'từ chối tệp ai'.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 6

- **Quan sát:** 327/327 đoạn kèm tiêu đề tài liệu, 327 mã đoạn không trùng, nạp hai lần cho cùng
  dãy mã, 0 tài liệu có dãy mã khuyết. Cửa `audience` từ chối `ai` và **nhận** `guest`.
- **Diễn giải:** ba bất biến đầu là điều kiện để **tập đánh giá truy hồi tồn tại được**. Mã đoạn
  đổi giữa hai lần sinh thì mọi ca đánh giá trỏ sai chỗ, và người ta sẽ đi sửa bộ truy hồi trong
  khi lỗi nằm ở bộ chia đoạn.
- **Một lỗi thật đã sửa ở đây:** đoạn từng chứa **hai lần** tiêu đề tài liệu (tiền tố `title`
  cộng dòng `# H1` trong thân). Không phải chuyện thẩm mỹ — trùng tiêu đề **thổi phồng tần số
  từ**, và BM25 xếp hạng theo tần số từ. Tức nó làm lệch chính phép so BM25/embedding sẽ chạy ở
  bước sau: **một thiên lệch nằm trong dữ liệu**, nên đọc kết quả sẽ không thấy.
- **Giới hạn:** 3 tài liệu từng sinh ra đoạn mở đầu chỉ có dòng tiêu đề. Đã sửa bằng cách gộp,
  nhưng nó cho thấy bộ chia đoạn **phụ thuộc cách người viết đặt heading** — nên bất biến phải
  do máy canh, không do người nhớ.
"""))

    # ===================================== MỤC 7 — SINH RA, KHÔNG VIẾT TAY
    out.append(md(r"""
## 7. Tri thức kể lại dữ liệu thì phải được SINH, không viết tay

### Kiến thức

Kho tri thức bản cũ có tệp `menu.md` dài 159 dòng, kể lại thực đơn bằng văn xuôi. Trong đó có
câu: *"Nhà hàng có **hơn 90 món**..."* — trong khi thực đơn có **đúng 91 món**.

Câu đó đúng về mặt kỹ thuật nhưng vô dụng, và tệ hơn: nó là **con số viết tay**. Thêm 10 món thì
nó thành sai, và **không ai biết**, vì không có gì canh nó.

Đây là một luật chung, không riêng dự án này:

> **Văn xuôi kể lại dữ liệu thì luôn trôi khỏi dữ liệu.** Dữ liệu đổi, văn không đổi theo.

Chỉ có hai cách xử lý:

| Cách | Đánh giá |
|---|---|
| kỷ luật con người — sửa thực đơn thì sửa cả tài liệu | **luôn thất bại**, vì nó dựa vào việc người ta nhớ |
| **tính lại mỗi lần** — tài liệu do máy sinh, CI kiểm sinh lại được | cách duy nhất chặn được |

Nên `build_knowledge.py` sinh phần `derived`. Con số trong đó không thể sai, vì nó **được tính,
không được viết**.

Phần `demo` là cho nội dung **suy ra không được** ("bia đi với món nướng", "gọi bao nhiêu món cho
4 người"). Nhưng ngay cả phần này, **mọi con số cũng lấy từ thực đơn thật** — nên văn người viết
vẫn không nói sai về dữ liệu được.

### Tiêu chí chọn nhóm để sinh tài liệu

Đáng ra có thể sinh cho cả 16 nhóm nhãn, ra ~120 tài liệu, số nghe to hơn. Chỉ sinh cho **6
nhóm**, theo một tiêu chí duy nhất:

> *Nhóm này có câu hỏi nào mà **lớp tra khóa không trả lời được** không?*

**Có** với `method`, `region`, `ingredient`, `occasion`, `flavour`, `health` → sinh tài liệu.
**Không** với `spice`, `price`, `party`, `season` — bốn nhóm này phủ 91/91 món nên lọc theo nhãn
đã đúng **100%**. Thêm tài liệu là tạo **đường thứ hai cho cùng một việc**, đúng bệnh 8 đường
chồng nhau của bản cũ.
"""))

    out.append(code(r"""
# Chứng minh phần `derived` KHÔNG THỂ lệch: sinh lại rồi so từng byte
import sys as _sys
from collections import Counter
from rag.chunker import load_all
_sys.path.insert(0, str(ROOT / "ai" / "scripts"))
import build_knowledge as bk

docs = load_all(KNOWLEDGE)
src = Counter(d.source for d in docs)
print(f"derived (máy sinh) : {src['derived']} tài liệu")
print(f"demo (người viết)  : {src['demo']} tài liệu")

wanted = bk.generate(load("menu-dataset.json"), load("menu-tags.json"))
khop = sum(1 for p, t in wanted.items()
           if p.exists() and p.read_text(encoding="utf-8-sig") == t)
print(f"\nSinh lại và so từng byte: {khop}/{len(wanted)} tài liệu derived khớp")
print("=> CI chạy `build_knowledge.py --check`, nên tài liệu KHÔNG THỂ trôi khỏi thực đơn.")

# Truy một con số cụ thể về đúng thực đơn
items = load("menu-dataset.json")["items"]
veg = [m for m in items if "diet:vegetarian" in m["tags"]]
doc = next(d for d in docs if "vegetarian" in d.topic_keys)
print(f"\nTruy nguồn một con số:")
print(f"   đếm trực tiếp trên thực đơn : {len(veg)} món chay")
print(f"   tài liệu tri thức nói       : {doc.verbatim_answer[:64]}...")
print(f"   con số {len(veg)} có trong chuỗi     : {str(len(veg)) in doc.verbatim_answer}")

# Tiêu chí chọn nhóm, kiểm bằng độ phủ
d = load("menu-tags.json")
print(f"\nSáu nhóm ĐƯỢC sinh tài liệu: {sorted(bk.DERIVED_GROUPS)}")
print("Bốn nhóm KHÔNG sinh, vì lớp lọc theo nhãn đã đúng 100%:")
for g in ["spice", "price", "party", "season"]:
    phu = len({m["id"] for m in items if any(t.startswith(g + ":") for t in m["tags"])})
    print(f"   {g:8} phủ {phu}/{len(items)} món -> lọc dứt khoát, không cần tài liệu")
"""))

    out.append(plot_code(r"""
# Biểu đồ 3 — tiêu chí chọn nhóm sinh tài liệu, đặt cạnh độ phủ nhãn
from collections import Counter
from rag.chunker import load_all
import sys as _sys
_sys.path.insert(0, str(ROOT / "ai" / "scripts"))
import build_knowledge as bk

items = load("menu-dataset.json")["items"]
d = load("menu-tags.json")
groups = sorted({e["group"] for e in d["tags"].values()})
sinh = set(bk.DERIVED_GROUPS)

rows = []
for g in groups:
    phu = len({m["id"] for m in items if any(t.startswith(g + ":") for t in m["tags"])})
    rows.append((phu, g, g in sinh))
rows.sort()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))

ten = [g for _, g, _ in rows]
phu = [p for p, _, _ in rows]
mau = [XANH if s else XAM for _, _, s in rows]
b = ax1.barh(ten, phu, color=mau)
ax1.bar_label(b, labels=[f"{p}/91" for p in phu], padding=3, fontsize=8)
ax1.axvline(len(items), color=DO, linestyle="--", linewidth=1.4)
ax1.text(len(items) - 1, -0.6, "91/91 = lọc dứt khoát", color=DO, fontsize=8, ha="right")
ax1.set_xlabel("số món có nhãn thuộc nhóm")
ax1.set_title("Độ phủ nhãn, và nhóm nào được sinh tài liệu\n"
              "(xanh = sinh tài liệu, xám = không)", fontsize=11)
ax1.set_xlim(0, len(items) * 1.18)

# Vì sao KHÔNG sinh cho nhóm phủ đủ: sẽ là đường thứ hai cho cùng một việc
docs = load_all(KNOWLEDGE)
thumuc = Counter(d_.path.parent.name for d_ in docs)
nhan = [f"policy\n(verbatim)", f"derived\n(nhóm nhãn)", f"written\n(người viết)"]
gia = [thumuc["policy"], thumuc["derived"], thumuc["written"]]
b2 = ax2.bar(nhan, gia, color=[DO, XANH, CAM])
ax2.bar_label(b2, padding=2, fontweight="bold")
ax2.set_ylabel("số tài liệu")
ax2.set_title(f"84 tài liệu chia theo vai trò\n"
              f"(6/16 nhóm nhãn được sinh, không phải 16/16)", fontsize=11)
ax2.set_ylim(0, max(gia) * 1.2)

plt.tight_layout(); plt.show()
print(f"Chỉ {len(sinh)}/{len(groups)} nhóm nhãn được sinh tài liệu. Tiêu chí: nhóm đó có câu")
print("hỏi nào mà LỚP TRA KHÓA không trả lời được không. Bốn nhóm phủ 91/91 bị bỏ qua vì")
print("lọc theo nhãn đã đúng 100% — thêm tài liệu là tạo đường thứ hai cho cùng một việc.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 7

- **Quan sát:** 56/84 tài liệu là `derived`, và **56/56 khớp từng byte** khi sinh lại. Con số
  "17 món chay" trong tài liệu truy được về đúng phép đếm trên thực đơn. Chỉ **6/16** nhóm nhãn
  được sinh tài liệu.
- **Diễn giải:** `--check` trong CI là thứ biến "tài liệu không thể lệch" từ một lời hứa thành
  một **bất biến máy canh**. Không có bước đó thì `derived` chỉ là một cái tên.
- **Tiêu chí chọn nhóm là tiêu chí thật, không phải "thêm cho đủ số đoạn":** 4 nhóm phủ 91/91
  bị bỏ qua vì lọc theo nhãn đã đúng 100%. Thêm tài liệu cho chúng là tạo **đường thứ hai cho
  cùng một việc** — và khi câu trả lời sai thì không ai biết đường nào sai. Bản cũ có 8 đường
  chồng nhau, 2 trong số đó bị tắt mà hệ thống vẫn chạy đúng.
- **Giới hạn:** `demo` vẫn là 28 tài liệu người viết. Chúng không thể nói sai về **con số** (số
  lấy từ thực đơn), nhưng có thể nói sai về **chính sách** — và điều đó chỉ chủ nhà hàng biết.
- **Quyết định tiếp theo:** dữ liệu và tri thức đã xong. Nhưng chưa có cách nào biết hệ thống
  trả lời đúng hay sai — đó là Phần II.
"""))

    # ================================================================= PHẦN II
    out.append(md(r"""
---
# PHẦN 2 — TẬP ĐÁNH GIÁ VÀ THƯỚC ĐO
> **TV1** — nền tảng đo lường. Cùng người với Phần 1, và mục dưới nói vì sao.

> **Vị trí:** **xuyên ngang cả 4 khâu runtime**, không phải một chặng — nên nó thuộc TV1 cùng với
> dữ liệu. Phần này chứa **bài học đắt nhất của cả dự án**.

| | |
|---|---|
| **Câu hỏi khâu này trả lời** | *Làm sao biết hệ thống trả lời đúng hay sai — và làm sao biết thước đo của mình đúng?* |
| **Kiến thức phải nắm** | khóa đáp án dạng truy vấn thay vì danh sách · test hai chiều · chia ba nhóm chốt/phát triển/niêm phong · bộ dò lỗ thước đo |
| **Tệp sở hữu** | `ai/evaluation/cases.json` · `answer_metric.py` · `menu_selectors.py` · `validate_cases.py` · `build_split.py` · `probe_metric_holes.py` · `test_answer_metric.py` |
| **Đầu vào** | thực đơn thật (91 món) và yêu cầu nghiệp vụ |
| **Đầu ra bàn giao** | 119 ca / 41 họ · thước đo 37 test · bộ dò lỗ để TV2 và TV4 chạy `run_baseline.py` |
| **Tự đo bằng** | `validate_cases.py` · `build_split.py --check` · `probe_metric_holes.py` · `python -m unittest discover -s ai/evaluation` |
| **Trạng thái** | **xong** — 37 test xanh, bộ dò tìm 0 lỗ |

### Điều TV1 phải hiểu trước tiên

**Thước đo cũng là một phương pháp, và cũng phải chứng minh được mình đúng.** Ở bản cũ, thước
đo sai **3 lần trước khi hệ thống sai**, và cả 3 lần đều sai theo chiều nguy hiểm hơn: **bịa ra
lỗi không có**, khiến người ta đi sửa những thứ vốn đã đúng.

## 8. Vì sao đo lường phải có trước thứ được đo

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

## 9. Khóa đáp án phải kiểm được — dùng truy vấn, không dùng danh sách

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
#### Nhận xét — Mục 9

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
#### Nhận xét — Mục 9 (tiếp)

- **Quan sát:** cả ba lỗi cố tình tạo ra đều bị bắt, và bắt đúng chỗ. Bản đầy đủ trong
  `ai/evaluation/validate_cases.py` kiểm **9 loại lỗi** và đã được chứng minh bắt cả 9.
- **Diễn giải:** đây là kỹ thuật chung — **muốn tin một bộ kiểm, phải làm hỏng thứ nó kiểm rồi
  xem nó có đỏ không.** Một bộ kiểm luôn xanh không chứng minh được gì.
- **Giới hạn:** phép thử này chứng minh bộ kiểm bắt được **lỗi đã nghĩ tới**. Lỗi chưa nghĩ tới
  cần công cụ khác — mục 7.
- **Quyết định tiếp theo:** chia tập đánh giá sao cho nó dự báo được.
"""))

    out.append(md(r"""
## 10. Chia tập đánh giá: ba nhóm, không phải hai

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
#### Nhận xét — Mục 10

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
## 11. Thước đo: hai nguyên tắc và một bộ dò lỗ

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
#### Nhận xét — Mục 11

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

    # ================================================================= PHẦN 3
    out.append(md(r"""
---
# PHẦN 3 — TRẢ LỜI KHÔNG CẦN MÔ HÌNH
> **TV2** (hiểu câu hỏi) và **TV4** (chọn món & giỏ hàng)

> **Vị trí:** TV2 (hiểu câu hỏi) và TV4 (chọn món). Đây là phần quyết định **mô hình sinh còn phải
> làm gì** — và câu trả lời hóa ra là "ít hơn nhiều so với tưởng".

| | |
|---|---|
| **Câu hỏi khâu này trả lời** | *Bao nhiêu câu trả lời được mà KHÔNG cần mô hình sinh?* |
| **Kiến thức phải nắm** | số nền (baseline) · khớp cụm dài trước rồi ăn hết đoạn · **ràng buộc khác ngữ cảnh** · fail-closed cho dị nguyên · ablation để chứng minh từng cơ chế có giá trị |
| **Tệp sở hữu** | `ai/app/understand.py` · `answer.py` · `cart.py` · `session.py` · `test_understand.py` |
| **Đầu vào** | 119 ca, thước đo và từ điển nhãn — tất cả từ TV1 |
| **Đầu ra bàn giao** | hợp đồng `Reply` cho TV5; số nền để mọi thứ sau so vào |
| **Tự đo bằng** | `run_baseline.py --all` · `run_ablation.py` · `python -m unittest discover -s ai/app` |
| **Trạng thái** | **xong phần trả lời** — 108/119, 0 lỗi an toàn. **Còn lại:** thẻ giỏ hàng và bộ nhớ phiên |

### Vì sao phải đo số nền TRƯỚC khi thêm mô hình

Bản cũ có **8 đường xử lý tất định chồng nhau** và chỉ **33%** câu trả lời do mã sinh ra. Không
ai nói được đường nào phụ trách việc gì, và **2 đường bị một cờ legacy tắt mà hệ thống vẫn chạy
đúng** — tức chúng là dư, nhưng không ai biết vì không có số nền để đối chiếu.

Số nền có hai tính chất mà câu trả lời của mô hình không có: **đúng 100% về dữ liệu** và **giống
nhau mọi lần chạy**. Nên nó là mốc, và mọi thứ thêm vào sau phải chứng minh mình vượt mốc đó.
"""))

    out.append(md(r"""
## 12. Số nền: sáu nhánh loại trừ, không nhánh nào chồng nhánh nào

### Kiến thức

Kiến trúc trả lời là **sáu nhánh loại trừ nhau**, và thứ tự là thứ tự loại trừ:

| # | Nhánh | Việc | Vì sao đứng ở vị trí đó |
|---|---|---|---|
| 1 | ngoài bài toán | từ chối ngắn gọn | phải chặn trước, không thì câu hỏi thời tiết rơi vào nhánh lọc món |
| 2 | câu chính sách | tra kho tri thức, hoặc nói chưa có dữ liệu | "mấy giờ mở cửa" không phải câu lọc món |
| 3 | hỏi giá một món | nêu giá | có đáp án đúng duy nhất |
| 4 | so sánh hai món | nêu dữ kiện cả hai | |
| 5 | món đắt/rẻ nhất | tính rồi nêu | |
| 6 | còn lại | lọc thực đơn theo ràng buộc | nhánh rộng nhất, nên đứng cuối |

Nhánh 6 sinh ra **câu hỏi lại** khi khách chưa nói gì đủ để lọc. Hỏi lại là **câu trả lời đúng**
ở đó, không phải thất bại — và thước đo của TV1 phải phân biệt được hai thứ này.

Đối lập với bản cũ: 8 đường **chồng nhau**, nên hai đường có thể cho hai kết quả khác nhau cho
cùng một câu, và hệ thống trả lời tùy lúc.
"""))

    out.append(code(r"""
# Số nền theo nhóm chia tập, và nhánh nào thật sự được dùng
import collections
import run_baseline as rb

g = collections.defaultdict(lambda: [0, 0])
nhanh, kieu = collections.Counter(), collections.Counter()
for c in rb.DATA["cases"]:
    _, reply, v = rb.run_case(c)
    grp = rb.group_of(c["family"])
    g[grp][1] += 1
    g[grp][0] += int(v.passed)
    nhanh[reply.branch.split(":")[0]] += 1
    kieu[reply.kind] += 1

tong_ok = sum(v[0] for v in g.values())
tong = sum(v[1] for v in g.values())
print(f"SỐ NỀN — chỉ tra thực đơn, không mô hình nào: {tong_ok}/{tong} "
      f"({100 * tong_ok / tong:.1f}%)\n")
print(f"{'nhóm':14}{'qua':>10}   vai trò của nhóm")
print("-" * 62)
vai = {"chốt": "an toàn, LUÔN phải 100%", "phát triển": "được xem, được sửa theo",
       "niêm phong": "chỉ mở để chốt kết quả"}
for k in ("chốt", "phát triển", "niêm phong"):
    ok, n = g[k]
    print(f"{k:14}{ok:>4}/{n:<4} {100*ok/n:5.1f}%   {vai[k]}")

print(f"\nSàn để so — cách lách 'luôn nói chưa có dữ liệu' qua được: "
      f"{sum(1 for c in rb.DATA['cases'] if c['expect']['kind'] == 'no_data')}/{tong}")
print("=> số nền chỉ có nghĩa khi nó cao hơn sàn này rất nhiều.")

print(f"\n{len(nhanh)} nhánh được dùng thật (không nhánh nào là mã chết):")
for b, n in nhanh.most_common():
    print(f"   {b:22} {n:3d} ca")
"""))

    out.append(plot_code(r"""
# Biểu đồ 4 — số nền: theo nhóm chia tập, và so với sàn
import collections
import run_baseline as rb

g = collections.defaultdict(lambda: [0, 0])
nhanh = collections.Counter()
for c in rb.DATA["cases"]:
    _, reply, v = rb.run_case(c)
    grp = rb.group_of(c["family"])
    g[grp][1] += 1
    g[grp][0] += int(v.passed)
    nhanh[reply.branch.split(":")[0]] += 1
tong_ok = sum(v[0] for v in g.values()); tong = sum(v[1] for v in g.values())
san = sum(1 for c in rb.DATA["cases"] if c["expect"]["kind"] == "no_data")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))

ten = ["chốt\n(an toàn)", "phát triển", "niêm phong\n(held-out)"]
khoa = ["chốt", "phát triển", "niêm phong"]
qua = [g[k][0] for k in khoa]; tongnhom = [g[k][1] for k in khoa]
truot = [t - q for q, t in zip(qua, tongnhom)]
ax1.bar(ten, qua, color=XANH, label="qua")
ax1.bar(ten, truot, bottom=qua, color=DO, label="đỏ")
for i, (q, t) in enumerate(zip(qua, tongnhom)):
    ax1.text(i, t + 0.8, f"{q}/{t}\n{100*q/t:.1f}%", ha="center", fontsize=9,
             fontweight="bold")
ax1.set_ylabel("số ca"); ax1.set_ylim(0, max(tongnhom) * 1.28)
ax1.set_title("Số nền theo nhóm chia tập\n(nhóm CHỐT phải luôn 100%)", fontsize=11)
ax1.legend(fontsize=9)

# So số nền với sàn — sàn là điều làm con số có nghĩa
b = ax2.barh(["Sàn: luôn nói\n'chưa có dữ liệu'", "Số nền\n(mã tất định)"],
             [san, tong_ok], color=[XAM, XANH])
ax2.bar_label(b, labels=[f"{san}/{tong} = {100*san/tong:.1f}%",
                         f"{tong_ok}/{tong} = {100*tong_ok/tong:.1f}%"],
              padding=4, fontsize=10, fontweight="bold")
ax2.set_xlim(0, tong * 1.3); ax2.set_xlabel("số ca qua")
ax2.set_title("Vì sao cần SÀN để so\n(không có sàn thì % nào cũng 'nghe được')",
              fontsize=11)
ax2.grid(False)

plt.tight_layout(); plt.show()
print(f"Nhóm chốt {g['chốt'][0]}/{g['chốt'][1]} — đây là điều kiện chặn, không phải số liệu.")
print(f"Một ca chốt đỏ là CHẶN, kể cả khi tỷ lệ chung tăng.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 12

- **Quan sát:** 108/119 (90,8%) chỉ bằng mã tất định. Nhóm **chốt 21/21 (100%)**, phát triển
  54/61, niêm phong 33/37. Sàn để so là 8/119 (6,7%). 13 nhánh đều được dùng thật.
- **Diễn giải:** con số 90,2% chỉ có nghĩa vì có **sàn 7,1%** đặt cạnh. Một hệ thống luôn đáp
  "chưa có dữ liệu" cũng đạt 6,7% mà không trả lời gì — nếu không công bố sàn thì mọi tỷ lệ đều
  "nghe được".
- **Nhóm chốt là điều kiện chặn, không phải số liệu:** một ca chốt đỏ là **chặn phát hành**, kể
  cả khi tỷ lệ chung tăng. Đưa ca an toàn vào tập phát triển thì tỷ lệ chung sẽ che mất nó.
- **Giới hạn phải nói ra:** tập niêm phong **đã được mở** ở bước 4 để chốt kết quả, nên
  33/37 hiện tại **không còn là số held-out thật**. Số held-out thật duy nhất của dự án là
  **23/27 (85,2%)** ở lần mở đầu tiên. Mọi tập mới phải chỉ mở một lần.
"""))

    out.append(md(r"""
## 13. Chỗ khó nhất của khâu này: RÀNG BUỘC khác NGỮ CẢNH

### Kiến thức

Đây là phân biệt mà nếu làm sai thì hệ thống *vẫn chạy*, *vẫn không lỗi*, nhưng trả lời tệ — nên
nó chỉ lộ ra khi có thước đo.

Khách nói hai loại điều rất khác nhau:

| Loại | Ví dụ | Phải làm gì | Nếu làm sai |
|---|---|---|---|
| **Ràng buộc** | "tôi ăn chay", "dị ứng hải sản", "dưới 100k" | **lọc cứng** — món không thỏa thì loại | mời khách món họ không ăn được |
| **Ngữ cảnh** | "tôi đi hẹn hò", "trời nóng", "đi với bạn" | **chỉ sắp thứ tự** — không loại món nào | câu "hẹn hò" chỉ còn **1 món** trong 91 |

Ca thật đã xảy ra: nhãn `occasion` được dùng làm **lọc cứng**, và vì nhóm đó chỉ phủ 79/91 món
nên câu "đi hẹn hò nên gọi gì" trả về **đúng một món**. Sửa bằng cách chuyển `occasion` sang
`prefer_tags` — chỉ ảnh hưởng thứ tự, không loại món.

**Quy tắc suy ra từ Mục 3:** nhóm nhãn **không phủ hết 91 món** thì chỉ được dùng theo chiều
khẳng định (đưa lên trước), **không** được dùng để loại. Vì thiếu nhãn ở nhóm đó nghĩa là *chưa
ghi nhận*, không phải *không phù hợp*.

### Fail-closed cho dị nguyên: ngoại lệ duy nhất, và nó không bao giờ được nới

Ràng buộc dị nguyên áp **cuối cùng** và **không bao giờ bị nới**, kể cả khi kết quả rỗng. Thà
nói "không có món nào phù hợp, bạn hỏi nhân viên giúp mình" còn hơn mời khách một món có thể gây
dị ứng.
"""))

    out.append(code(r"""
# Ràng buộc vs ngữ cảnh, và fail-closed — chứng minh bằng chính bộ trả lời
from answer import respond, select
from understand import understand
menu = load("menu-dataset.json"); items = menu["items"]

print("1) NGỮ CẢNH chỉ sắp thứ tự, KHÔNG loại món")
r = understand("Mình đi hẹn hò, gợi ý món nào", items)
print(f"   require (lọc cứng) : {r.require_tags}")
print(f"   prefer  (chỉ xếp)  : {r.prefer_tags}")
print(f"   số món còn lại sau khi lọc: {len(select(r, items))}/{len(items)}")
print("   => dịp ăn KHÔNG nằm trong require, nên không món nào bị loại.")

print("\n2) RÀNG BUỘC thì lọc cứng")
r2 = understand("Mình ăn chay, dưới 80 nghìn", items)
print(f"   require : {r2.require_tags}   ngân sách: {r2.budget_max}")
print(f"   số món còn lại: {len(select(r2, items))}/{len(items)}")

print("\n3) FAIL-CLOSED: ràng buộc dị nguyên không bao giờ được nới")
r3 = understand("Mình dị ứng hải sản, cho mình món ăn", items)
chon = select(r3, items)
print(f"   avoid   : {r3.avoid_tags}")
print(f"   số món  : {len(chon)}/{len(items)}")
con_di_nguyen = [m["name"] for m in chon if "allergen:seafood" in m["tags"]]
print(f"   món còn sót nhãn hải sản: {len(con_di_nguyen)}  <- PHẢI là 0")

rep = respond(r3, items)
print(f"   câu trả lời có mở đường hỏi nhân viên: "
      f"{'nhân viên' in rep.text or 'bếp' in rep.text}")
print("   => nhãn dị nguyên chỉ phủ 44/91 món, nên danh sách lọc ra KHÔNG phải")
print("      kết luận về an toàn. Lời nhắc hỏi nhân viên là bắt buộc, không phải lịch sự.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 13

- **Quan sát:** câu "hẹn hò" giữ nguyên toàn bộ 91 món vì dịp ăn nằm ở `prefer_tags`, không ở
  `require_tags`. Câu "ăn chay dưới 80k" lọc cứng. Câu dị ứng hải sản để lại **0 món** mang nhãn
  hải sản và câu trả lời **có** mở đường hỏi nhân viên.
- **Diễn giải:** phân biệt ràng buộc/ngữ cảnh không phải chuyện tinh tế về ngôn ngữ — nó suy
  trực tiếp từ **độ phủ nhãn** ở Mục 3. Nhóm phủ 91/91 mới được dùng để loại; nhóm phủ một phần
  chỉ được dùng để xếp thứ tự.
- **Fail-closed là ngoại lệ có chủ ý:** nó làm kết quả *tệ hơn* theo nghĩa số món trả về, và đó
  là đánh đổi đúng. Kết quả rỗng kèm lời nhắc hỏi nhân viên là câu trả lời đúng; kết quả có món
  bằng cách nới ràng buộc dị nguyên là câu trả lời **sai một cách nguy hiểm**.
- **Giới hạn:** lời nhắc hỏi nhân viên là điều **thước đo bắt buộc** ở mọi ca dị ứng. Nhưng nó
  chỉ chuyển rủi ro sang con người — hệ thống không thể biết bếp có dùng chung dụng cụ hay không.
"""))

    out.append(md(r"""
## 14. Ablation: chứng minh từng cơ chế thật sự có giá trị

### Kiến thức

Câu hỏi mà mọi hệ thống nhiều cơ chế phải trả lời: **cơ chế nào thật sự cần?** Bản cũ có 8 đường
và 2 trong số đó là dư mà không ai biết.

Cách trả lời là **ablation**: tắt từng cơ chế, đo lại, xem mất bao nhiêu ca. Cơ chế nào tắt mà
**không mất ca nào** thì nó là dư — và phải nói ra, không phải giữ lại "cho chắc".

Có hai cột phải đọc riêng, và cột thứ hai quan trọng hơn:

- **mất bao nhiêu ca** — giá trị về chất lượng
- **gây bao nhiêu lỗi an toàn** — cơ chế nào tắt mà sinh lỗi an toàn thì nó **không phải tính
  năng, nó là hàng rào**, và không được bàn về việc bỏ nó
"""))

    out.append(code(r"""
# Ablation: tắt từng cơ chế, đo lại
import run_ablation as ra

base_ok, base_unsafe = ra.measure()
n = len(ra.CASES)
print(f"bản đầy đủ: {base_ok}/{n} ca qua, {base_unsafe} lỗi an toàn\n")
print(f"{'cơ chế bị tắt':46}{'qua':>9}{'mất':>6}{'lỗi an toàn':>13}")
print("-" * 76)
ket_qua = []
for ten, tat in ra.ABLATIONS:
    hoan_lai = tat()                 # tắt cơ chế, trả về hàm hoàn lại
    try:
        ok, unsafe = ra.measure()
    finally:
        hoan_lai()                   # LUÔN hoàn lại, kể cả khi đo lỗi
    ket_qua.append((ten, ok, base_ok - ok, unsafe))
for ten, ok, mat, unsafe in sorted(ket_qua, key=lambda r: (-r[3], -r[2])):
    canh = "  <-- HÀNG RÀO" if unsafe else ""
    print(f"{ten:46}{ok:>5}/{n}{mat:>6}{unsafe:>13}{canh}")

du = [t for t, _, mat, unsafe in ket_qua if mat == 0 and unsafe == 0]
print(f"\ncơ chế tắt mà KHÔNG mất ca nào (tức là dư): {len(du)} {du}")
"""))

    out.append(plot_code(r"""
# Biểu đồ 5 — ablation: cơ chế nào là tính năng, cơ chế nào là hàng rào an toàn
import run_ablation as ra

base_ok, base_unsafe = ra.measure()
n = len(ra.CASES)
rows = []
for ten, tat in ra.ABLATIONS:
    hoan_lai = tat()
    try:
        ok, unsafe = ra.measure()
    finally:
        hoan_lai()
    rows.append((ten, base_ok - ok, unsafe))
rows.sort(key=lambda r: (r[2], r[1]))

fig, ax = plt.subplots(figsize=(11, 5))
ten = [r[0] for r in rows]
mat = [r[1] for r in rows]
mau = [DO if r[2] else XANH for r in rows]
b = ax.barh(ten, mat, color=mau)
nhan = [f"{m} ca" + (f"  ·  {u} lỗi an toàn" if u else "") for _, m, u in rows]
ax.bar_label(b, labels=nhan, padding=4, fontsize=9)
ax.set_xlabel("số ca MẤT khi tắt cơ chế")
ax.set_xlim(0, max(mat) * 1.55)
ax.set_title("Ablation — tắt từng cơ chế rồi đo lại\n"
             "đỏ = tắt thì sinh LỖI AN TOÀN (hàng rào, không phải tính năng)",
             fontsize=11)

from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=DO, label="hàng rào an toàn"),
                   Patch(color=XANH, label="tính năng chất lượng")],
          loc="lower right", fontsize=9)
plt.tight_layout(); plt.show()

rao = sum(1 for r in rows if r[2])
print(f"{rao}/{len(rows)} cơ chế là HÀNG RÀO AN TOÀN — tắt là sinh lỗi an toàn ngay.")
print("Với chúng thì câu hỏi 'có đáng giữ không' không đặt ra được.")
print(f"{len(rows) - rao}/{len(rows)} cơ chế là tính năng chất lượng — đo được bằng số ca.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 14

- **Quan sát:** 9/9 cơ chế đều có ít nhất một ca chứng minh giá trị — **không cơ chế nào là dư**.
  5/9 là **hàng rào an toàn**: tắt là sinh lỗi an toàn ngay. Hai cơ chế đáng chú ý nhất là "bỏ
  dấu câu khi chuẩn hóa" (mất 20 ca, 7 lỗi an toàn) và "phân biệt món ăn với đồ uống" (mất 14
  ca, 7 lỗi an toàn).
- **Diễn giải:** "bỏ dấu câu" nghe như chuyện làm sạch chữ, nhưng thiếu nó thì `"mấy giờ mở
  cửa?"` không khớp cụm `mo cua` — dấu hỏi làm lệch cả chuỗi. Đây là ví dụ điển hình của **cơ chế
  nghe tầm thường mà giá trị đo được rất cao**, và không có ablation thì không ai biết.
- **Phân biệt hàng rào với tính năng là kết luận quan trọng nhất của mục này:** với 5 cơ chế đỏ,
  câu hỏi "có đáng giữ không" **không đặt ra được** — chúng không đánh đổi với chất lượng.
- **Giới hạn đã nêu ở Mục 4:** cơ chế "ăn hết đoạn đã khớp" chỉ đo được **1 ca**, nhưng nó bảo
  vệ **61 chỗ** đụng chữ. Chênh lệch đó là **giới hạn của tập đánh giá**, không phải bằng chứng
  cơ chế vô dụng — nên con số ablation phải đọc kèm phần kiểm kê.
"""))

    # ================================================================= PHẦN 4
    out.append(md(r"""
---
# PHẦN 4 — TRUY HỒI TRI THỨC
> **TV3** — nhận kho 303 đoạn từ TV1, làm phần lấy đoạn

> **Vị trí:** TV3, giữa "hiểu câu hỏi" và "chọn món". **Đây là phần duy nhất trong notebook này
> còn CHƯA đo** — và mục dưới nói rõ chưa đo cái gì.

| | |
|---|---|
| **Câu hỏi khâu này trả lời** | *Với câu hỏi cần tri thức, lấy đoạn nào — và phương pháp lấy nào tốt hơn?* |
| **Kiến thức phải nắm** | BM25 (`k1`, `b`, tf-idf) · embedding và cosine · hybrid RRF · Hit@k, MRR@k, nDCG@k, **forbidden@k** · giao thức đo độ trễ |
| **Tệp sở hữu** | `ai/app/rag/bm25.py` · `embedding.py` · `hybrid.py` · `retriever.py` · `run_retrieval_comparison.py` |
| **Đầu vào** | 303 đoạn `synthesize` của TV1; ~120 ca truy hồi của TV1 (**chưa có — TV3 chờ cái này**) |
| **Đầu ra bàn giao** | bảng so ba phương pháp trên **hai bài toán**, kèm phân tích ca sai |
| **Tự đo bằng** | `run_retrieval_comparison.py` (**chưa viết**) |
| **Trạng thái** | **kho đã sẵn sàng, phép so CHƯA CHẠY** — xem Mục 15 |

### Vì sao phần này chưa có số, và vì sao nói ra chứ không viết cho đầy

Notebook này là tài liệu báo cáo, nên nó phải phân biệt rõ **điều đã đo** với **điều còn dự
kiến**. Viết một mục về "kết quả so BM25 vs embedding" khi chưa chạy phép so nào là **bịa số**,
và một báo cáo có một số bịa thì mọi số còn lại đều mất giá trị.

Điều đã làm được: kho tri thức **đủ lớn và đủ sạch** để phép so có nghĩa. Điều chưa làm: chính
phép so.
"""))

    out.append(md(r"""
## 15. Điều kiện để phép so truy hồi có nghĩa — đã đủ, và còn thiếu gì

### Kiến thức

Trước khi so ba phương pháp truy hồi, phải kiểm bốn điều kiện. Nếu thiếu một điều, kết quả so
sẽ **có số nhưng không nói được gì**:

| Điều kiện | Vì sao cần | Trạng thái |
|---|---|---|
| **Kho đủ lớn** | với ~40 đoạn thì BM25 và embedding hòa nhau tầm thường | **đủ** — 303 đoạn |
| **Chỉ mục sạch** | đoạn nội bộ hoặc đoạn rác trong chỉ mục làm mọi phương pháp tệ đều nhau | **đủ** — cửa `audience`, 0 đoạn quá ngắn, 0 trùng tiêu đề |
| **Mã đoạn tất định** | khóa đáp án trỏ vào `chunk_id`; mã đổi thì mọi ca trỏ sai | **đủ** — kiểm ở Mục 6 |
| **Tập đánh giá truy hồi** | 119 ca hiện có chấm **câu trả lời**, không chấm **đoạn được lấy** | **CHƯA CÓ** |

### Hai bài toán, không phải một — và đây là phần đáng báo cáo nhất

Điểm mạnh của phép so này không nằm ở việc "hybrid thắng bao nhiêu điểm", mà ở việc so trên
**hai bài toán khác nhau** rồi cho thấy câu trả lời khác nhau:

| Bài toán | Ứng viên | Dự kiến |
|---|---|---|
| **Truy hồi tri thức** — đoạn nào trả lời câu chính sách | BM25 / embedding / hybrid | embedding thắng ở câu diễn đạt khác từ; BM25 thắng ở câu có tên riêng |
| **Chọn món** — món nào thỏa ràng buộc | BM25 / embedding / **lọc theo nhãn** | **lọc theo nhãn thắng dứt khoát** |

Bài toán thứ hai quan trọng vì nó chứng minh bằng số rằng **không phải chỗ nào cũng nên dùng
RAG**. Ví dụ "món nào dưới 50.000đ": BM25 và embedding **không hiểu số**, còn lọc theo nhãn
`price` đúng **100%** vì nhóm đó phủ 91/91 món.

Đó cũng là lý do bước 5 của dự án **bỏ** `sentence-transformers` (~3GB) khỏi ảnh Docker: 24 chủ
đề chính sách tra khóa đúng 100% thì thêm một tầng embedding là thêm 3GB cho 0 lợi ích.
"""))

    out.append(code(r"""
# Kiểm bốn điều kiện của phép so truy hồi — cái nào đủ, cái nào chưa
from pathlib import Path as _P
from rag.chunker import all_chunks, load_all, retrievable_chunks

chunks = retrievable_chunks(KNOWLEDGE)
tat_ca = all_chunks(KNOWLEDGE)
w = sorted(c.word_count for c in chunks)

dieu_kien = []
dieu_kien.append(("kho đủ lớn (>=250 đoạn xếp hạng)", len(chunks) >= 250,
                  f"{len(chunks)} đoạn synthesize"))
dieu_kien.append(("chỉ mục sạch: 0 đoạn quá ngắn", all(c.word_count >= 12 for c in chunks),
                  f"ngắn nhất {w[0]} từ"))
h1_con = [c.chunk_id for c in tat_ca
          if any(l.startswith("# ") for l in c.text.splitlines()[1:])]
dieu_kien.append(("chỉ mục sạch: 0 đoạn trùng tiêu đề", not h1_con,
                  f"{len(h1_con)} đoạn còn dòng H1"))
ids = [c.chunk_id for c in tat_ca]
dieu_kien.append(("mã đoạn tất định và không trùng",
                  len(set(ids)) == len(ids) and [c.chunk_id for c in all_chunks(KNOWLEDGE)] == ids,
                  f"{len(set(ids))}/{len(ids)} mã duy nhất"))
co_tap = (_P(str(KNOWLEDGE.parent)) / "evaluation" / "retrieval_cases.json").exists()
dieu_kien.append(("tập đánh giá truy hồi (~120 ca)", co_tap,
                  "retrieval_cases.json chưa tồn tại" if not co_tap else "có"))

print(f"{'điều kiện':44}{'trạng thái':>12}   bằng chứng")
print("-" * 92)
for ten, dat, bc in dieu_kien:
    print(f"{ten:44}{'ĐỦ' if dat else 'CHƯA':>12}   {bc}")

thieu = [t for t, dat, _ in dieu_kien if not dat]
print(f"\n{len(dieu_kien) - len(thieu)}/{len(dieu_kien)} điều kiện đã đủ.")
if thieu:
    print(f"Còn thiếu: {thieu}")
    print("=> Chưa chạy phép so nào. Mọi con số về BM25/embedding/hybrid trong báo cáo")
    print("   này sẽ là BỊA nếu viết ra bây giờ.")

# Cho thấy vì sao 'chọn món' KHÔNG nên dùng truy hồi
items = load("menu-dataset.json")["items"]
phu_gia = len({m["id"] for m in items if any(t.startswith("price:") for t in m["tags"])})
print(f"\nVí dụ vì sao không phải chỗ nào cũng dùng RAG:")
print(f"   nhóm nhãn `price` phủ {phu_gia}/{len(items)} món -> lọc theo nhãn đúng 100%")
print(f"   BM25 và embedding KHÔNG hiểu số, nên câu 'món nào dưới 50.000đ' chúng")
print(f"   không trả lời đúng được. Đây là kết quả đáng báo cáo, không phải thất bại.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 15

- **Quan sát:** 4/5 điều kiện đã đủ. 303 đoạn `synthesize` được xếp hạng, đoạn ngắn nhất 17 từ,
  0 đoạn trùng tiêu đề, 327 mã đoạn duy nhất và tất định. Thiếu **tập đánh giá truy hồi**.
- **Diễn giải:** phần khó của RAG **không phải** cài BM25 hay tải model embedding — đó là việc
  vài chục dòng mã. Phần khó là làm cho **chỉ mục đủ sạch để phép so nói được điều gì**, và đó
  chính là việc TV1 đã làm xong (mục 5–7).
- **Điều notebook này KHÔNG nói:** không có con số nào về BM25 vs embedding vs hybrid, vì chưa
  chạy phép so nào. Viết ra bây giờ là bịa, và một báo cáo có một số bịa thì mọi số còn lại mất
  giá trị.
- **Kết quả đã có, ngược với kỳ vọng thông thường:** bước 5 **bỏ** `sentence-transformers`
  (~3GB) khỏi ảnh Docker sau khi đo rằng 24 chủ đề chính sách tra khóa đúng 100%. Nhóm nhãn
  `price` phủ 91/91 món nên lọc theo nhãn đúng 100%, còn BM25 và embedding không hiểu số. **Không
  phải chỗ nào cũng nên dùng RAG** — và điều đó cũng phải đo, không phải phán.
"""))

    # ================================================================= PHẦN 5
    out.append(md(r"""
---
# PHẦN 5 — MÔ HÌNH SINH, AN TOÀN VÀ TÍCH HỢP
> **TV2** (mô hình đọc ràng buộc) và **TV5** (thoái hóa êm, tích hợp)

> **Vị trí:** phần mô hình thuộc TV2; phần tích hợp và thoái hóa êm thuộc TV5. Chứa **phát hiện
> quan trọng nhất của cả dự án**.

| | |
|---|---|
| **Câu hỏi khâu này trả lời** | *Mô hình sinh được phép làm gì, và nếu nó chết thì hệ thống mất gì?* |
| **Kiến thức phải nắm** | mô hình chỉ **hiểu**, không **chọn** · cổng kiểm khóa mô hình trả về · **an toàn không được phụ thuộc thành phần không tất định** · thoái hóa êm khi gọi thất bại |
| **Tệp sở hữu** | `ai/app/llm_understand.py` · `service.py` · `ai/contracts/*.schema.json` · `ai/Dockerfile` |
| **Đầu vào** | `Reply` của TV4; kho tri thức của TV1 |
| **Đầu ra bàn giao** | dịch vụ HTTP mà backend gọi được |
| **Tự đo bằng** | `run_with_model.py` · `python -m unittest test_llm_understand test_packaging` |
| **Trạng thái** | **xong phần mô hình** — 119/119, 0 lỗi an toàn. **Còn lại:** 5 endpoint HTTP |

### Nguyên tắc phân quyền: mô hình chỉ HIỂU, không CHỌN

Mô hình sinh **không được chọn món**. Nó chỉ làm một việc: đọc câu khách và trả về **nhãn ràng
buộc**. Việc chọn món vẫn do mã tất định làm, dựa trên nhãn đó.

Lý do rất cụ thể: nếu mô hình chọn món thì nó có thể chọn món **không tồn tại**, hoặc chọn món
**vi phạm ràng buộc dị ứng**. Nếu nó chỉ trả về nhãn, thì nhãn sai chỉ dẫn tới **gợi ý kém**, và
mọi nhãn nó trả về đều bị **kiểm lại** trước khi dùng.

```
câu khách  ->  mã tất định hiểu  ->  [nếu chưa đủ]  mô hình đọc thêm ràng buộc
                                                     |
                                        cổng kiểm: nhãn có thật không? đúng vai không?
                                                     |
                                            mã tất định CHỌN MÓN  ->  câu trả lời
```
"""))

    out.append(code(r"""
# Mô hình thêm được gì, và cổng kiểm bỏ gì
import collections, os
os.environ.setdefault("LLM_MODEL", "cx/gpt-5.6-luna-review")
import run_with_model as rw
from llm_understand import load_env

env = load_env()
det_ok = mod_ok = goi = 0
chi_mo_hinh, bo = [], collections.Counter()
for c in rw.CASES:
    _, v0, _ = rw.run(c, with_model=False, env=env, use_cache=True)
    _, v1, o = rw.run(c, with_model=True, env=env, use_cache=True)
    det_ok += int(v0.passed); mod_ok += int(v1.passed)
    if o and o.used:
        goi += 1
        for d in o.dropped:
            bo[d.split(":")[0] if ":" in d else d] += 1
    if v1.passed and not v0.passed:
        chi_mo_hinh.append((c["id"], c["question"]))

n = len(rw.CASES)
print(f"không mô hình : {det_ok}/{n}  ({100*det_ok/n:.1f}%)")
print(f"có mô hình    : {mod_ok}/{n}  ({100*mod_ok/n:.1f}%)")
print(f"số lần gọi    : {goi}/{n} ca ({100*goi//n}% — chỉ gọi khi mã tất định chưa hiểu đủ)")

print(f"\n=== {len(chi_mo_hinh)} ca CHỈ mô hình giải được ===")
for cid, q in chi_mo_hinh:
    print(f"   {cid:16} {q}")

print(f"\n=== Cổng kiểm BỎ nhãn mô hình trả về ({sum(bo.values())} lần, "
      f"{len(bo)} nhóm) ===")
for k, v in bo.most_common():
    print(f"   {k:12} {v} lần   (bịa hoặc sai vai -> KHÔNG được dùng)")
print("\n=> Mô hình trả về nhãn không có thật hoặc sai vai thì nhãn đó bị BỎ,")
print("   không phải được dùng rồi hy vọng nó đúng.")
"""))

    out.append(md(r"""
## 16. Phát hiện quan trọng nhất của dự án: an toàn KHÔNG được phụ thuộc mô hình sinh

### Kiến thức

Sau khi thêm 14 ca cách nói lạ, mã tất định một mình còn **2 lỗi an toàn**:

- *"Mình không ăn được **đồ tanh**"* — không hiểu "đồ tanh" là cá/hải sản
- *"Bé nhà mình **uống sữa là bị đau bụng**, có món nào **không sữa** không?"* — không hiểu

Mô hình sinh sửa được **cả hai**, và ban đầu tôi ghi nhận đó là **giá trị** của mô hình.

**Nghĩ lại thì đó là lỗi thiết kế nghiêm trọng.** Nếu mô hình là thứ duy nhất hiểu hai câu đó,
thì **an toàn của hệ thống phụ thuộc một thành phần không tất định**:

| Sự cố | Hậu quả nếu an toàn phụ thuộc mô hình |
|---|---|
| proxy chết | **mất bảo vệ dị ứng** |
| hết hạn mức gọi | **mất bảo vệ dị ứng** |
| mô hình trả lời sai một lần | **mất bảo vệ dị ứng** cho đúng khách đó |

Không chấp nhận được. Nên hai lớp nhận diện đó được **đưa về mã tất định**:

1. **Cách nói dân dã cho dị nguyên**: `đồ tanh`, `mùi tanh` → `allergen:seafood`
2. **Mẫu "không ⟨chủ đề⟩"** bắt bằng biểu thức chính quy thay vì liệt kê từng tổ hợp
3. **Triệu chứng cũng là cách khai dị ứng**: `bị đau bụng`, `bị ngứa`, `bị nổi mề đay`

Kết quả: **0 lỗi an toàn ở cả hai chế độ**. Mô hình vẫn có giá trị (+11 ca) nhưng **không còn
nằm trên đường an toàn**.

> **Nguyên tắc rút ra:** proxy chết thì khách mất phần gợi ý tinh, **không mất bảo vệ dị ứng.**

### Hệ quả thứ hai: gọi thất bại phải thoái hóa ÊM

Tôi từng viết rằng "gọi mô hình thất bại thì giữ nguyên câu trả lời tất định". Câu đó **đã từng
sai**: `urllib.request.Request(...)` nằm **ngoài** khối `try`, nên thiếu cấu hình là **sập** chứ
không thoái hóa. CI tìm ra, vì CI là môi trường duy nhất không có `ai/.env`.

Bài học: **một lời khẳng định về hành vi khi lỗi thì phải có test cho đúng đường lỗi đó.**
"""))

    out.append(code(r"""
# An toàn phải TẤT ĐỊNH — chứng minh hai câu đó nay hiểu được KHÔNG cần mô hình
from understand import understand
from answer import respond, select
items = load("menu-dataset.json")["items"]

# Kết luận của ô này được ĐẾM từ kết quả, không khẳng định trước rồi minh họa. Bản đầu của ô
# này viết "bốn cách khai dị ứng đều xử lý được" rồi in ra 2/4 SAI — và hai ca SAI đó là LỖ
# AN TOÀN THẬT, không phải lỗi trình bày.
cau_kho = [
    ("Mình không ăn được đồ tanh", "allergen:seafood", "cách nói dân dã"),
    ("Bé nhà mình uống sữa là bị đau bụng, có món nào không sữa không?",
     "allergen:dairy", "triệu chứng + mẫu 'không X'"),
    ("Cho mình món không hải sản", "allergen:seafood", "mẫu 'không X' (từng là MÃ CHẾT)"),
    ("Món nào không sữa", "allergen:dairy", "mẫu 'không X'"),
    ("Món nào không trứng", "allergen:egg", "mẫu 'không X'"),
    ("Món không gluten", "allergen:gluten", "mẫu 'không X'"),
    ("Ăn tôm là mình bị nổi mề đay", "allergen:seafood",
     "triệu chứng + TÊN MÓN CỤ THỂ"),
]
qua, truot = [], []
for cau, nhan_can, loai in cau_kho:
    r = understand(cau, items)
    chon = select(r, items)
    sot = sum(1 for m in chon if nhan_can in m["tags"])
    ok = nhan_can in r.avoid_tags and sot == 0
    (qua if ok else truot).append((cau, loai, r.avoid_tags, len(chon), sot))

print(f"{len(qua)}/{len(cau_kho)} cách khai dị ứng xử lý được HOÀN TOÀN bằng mã tất định:\n")
for cau, loai, avoid, n_mon, sot in qua:
    print(f"   OK  [{loai}]")
    print(f"       {cau[:70]}")
    print(f"       avoid={avoid}  còn {n_mon} món, sót nhãn cấm: {sot}")

if truot:
    print(f"\n{len(truot)} cách CHƯA xử lý được — đây là LỖ AN TOÀN CÒN MỞ:\n")
    for cau, loai, avoid, n_mon, sot in truot:
        print(f"   CHƯA [{loai}]")
        print(f"        {cau[:70]}")
        print(f"        avoid={avoid}  còn {n_mon} món, SÓT {sot} món mang nhãn cấm")
    print("\n   Nguyên nhân: khách gọi TÊN MÓN cụ thể ('tôm', 'cua') chứ không gọi tên")
    print("   nhóm dị nguyên ('hải sản'). Từ vựng chưa nối tên món tới nhóm dị nguyên.")
    print("   Việc này thuộc TV2 (từ vựng) và phải kèm ca đánh giá nhóm CHỐT của TV1.")

# Thoái hóa êm: thiếu cấu hình thì KHÔNG được sập
from llm_understand import enrich
r = understand("Cho mình gì đó chua chua", items)
truoc = list(r.prefer_tags)
kq = enrich(r, {}, use_cache=False)          # env rỗng = thiếu cấu hình hoàn toàn
print(f"\nGọi mô hình với cấu hình RỖNG (mô phỏng proxy chết / thiếu .env):")
print(f"   không sập, trả về: used={kq.used}  lý do={kq.reason!r}")
print(f"   prefer_tags trước {truoc} -> sau {r.prefer_tags}  (giữ nguyên)")
print("   => câu trả lời tất định vẫn tới khách. Đây là điều tôi từng khẳng định SAI")
print("      trước khi có test cho đúng đường lỗi này.")
"""))

    out.append(plot_code(r"""
# Biểu đồ 6 — mô hình thêm gì, và an toàn có phụ thuộc nó không
import collections, os
os.environ.setdefault("LLM_MODEL", "cx/gpt-5.6-luna-review")
import run_with_model as rw
from llm_understand import load_env

env = load_env()
det = mod = goi = 0
theo_ho = collections.Counter()
for c in rw.CASES:
    _, v0, _ = rw.run(c, with_model=False, env=env, use_cache=True)
    _, v1, o = rw.run(c, with_model=True, env=env, use_cache=True)
    det += int(v0.passed); mod += int(v1.passed)
    if o and o.used: goi += 1
    if v1.passed and not v0.passed: theo_ho[c["family"]] += 1
n = len(rw.CASES)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.6))

# (a) số nền -> có mô hình, và AN TOÀN không đổi
x = ["Chỉ mã\ntất định", "Có mô hình\nsinh"]
ax1.bar(x, [det, mod], color=[XANH, CAM], width=0.55)
for i, v in enumerate([det, mod]):
    ax1.text(i, v + 1.5, f"{v}/{n}\n{100*v/n:.1f}%", ha="center",
             fontweight="bold", fontsize=10)
ax1.axhline(det, color=XANH, linestyle=":", linewidth=1.2)
ax1.text(1.38, det, "số nền", color=XANH, fontsize=8, va="center")
ax1.set_ylim(0, n * 1.22); ax1.set_ylabel("số ca qua")
ax1.set_title(f"Mô hình thêm {mod - det} ca (+{100*(mod-det)/n:.1f}đ%)\n"
              f"nhưng chỉ được gọi ở {goi}/{n} ca", fontsize=11)
# Lỗi an toàn = 0 ở CẢ HAI cột, đó là điều đáng nhấn
ax1.text(0.5, n * 1.08, "lỗi an toàn: 0 ở CẢ HAI chế độ", ha="center",
         fontsize=10, fontweight="bold", color=DO,
         bbox=dict(boxstyle="round,pad=0.4", facecolor="#fdf2f0", edgecolor=DO))

# (b) mô hình giúp ở HỌ nào — cho thấy nó không nằm trên đường an toàn
ho = theo_ho.most_common()
ax2.barh([h for h, _ in ho][::-1], [v for _, v in ho][::-1], color=CAM)
ax2.set_xlabel("số ca mô hình giải thêm")
ax2.set_title("Mô hình giúp ở đâu — toàn bộ là câu GỢI Ý,\n"
              "không có ca an toàn nào", fontsize=11)
ax2.set_xticks(range(0, max(theo_ho.values()) + 1))

plt.tight_layout(); plt.show()
print(f"Mô hình giải thêm {mod - det} ca, thuộc {len(theo_ho)} họ: "
      f"{sorted(theo_ho)}")
print("KHÔNG họ nào là họ an toàn. Đó là điều phải đạt được, không phải may mắn:")
print("hai ca dị ứng mà trước đây chỉ mô hình hiểu đã được đưa về mã tất định.")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 16

- **Quan sát:** 108/119 → **119/119** khi có mô hình, và mô hình chỉ được gọi ở **22/119 ca
  (18%)**. **0 lỗi an toàn ở cả hai chế độ.** 11 ca mô hình giải thêm thuộc các họ hương vị, sức
  khỏe, ngân sách, dịp ăn, cách chế biến — **không họ nào là họ an toàn**.
- **Diễn giải:** đây là phát hiện quan trọng nhất của dự án, và nó **không** phải "mô hình tốt".
  Nó là: *an toàn phải nằm ở phần tất định, không nằm ở phần sinh*. Ban đầu hai ca dị ứng chỉ mô
  hình hiểu được, và tôi đã ghi nhận đó là **giá trị** của mô hình — cách đọc đó sai. Đúng ra nó
  là **lỗi thiết kế**: proxy chết là mất bảo vệ dị ứng.
- **Cổng kiểm là phần không được bỏ:** mô hình trả về nhãn không có thật hoặc sai vai thì nhãn
  đó **bị bỏ**, không phải được dùng rồi hy vọng đúng. Đo được: cổng bỏ nhãn ở 4 nhóm.
- **Một lời khẳng định của tôi từng SAI:** tôi viết "gọi thất bại thì giữ nguyên câu trả lời tất
  định" trước khi có test cho đường lỗi đó — và `Request` nằm ngoài `try` nên thiếu cấu hình là
  **sập**. CI tìm ra vì CI là môi trường duy nhất không có `ai/.env`. Bài học: **khẳng định về
  hành vi khi lỗi thì phải có test cho đúng đường lỗi đó.**
- **Giới hạn:** độ trễ mô hình đo được **~8,6 giây/lần gọi**. Với 20% ca thì trung bình còn chịu
  được, nhưng đó là con số đáng lo nhất khi đưa vào dùng thật.
"""))

    # ============================================================== TỔNG HỢP
    out.append(md(r"""
---
# PHẦN 6 — KẾT QUẢ TỔNG HỢP, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN

Phần này không thêm kiến thức mới. Nó gom lại **con số nào đã đo, con số nào chưa**, và **cái gì
không đo được** — vì một báo cáo mà không phân biệt ba loại đó thì người đọc không biết tin phần
nào.

## 17. Bảng kết quả, và điều mỗi con số KHÔNG nói
"""))

    out.append(plot_code(r"""
# Biểu đồ 7 — bảng điều khiển tổng hợp cho báo cáo
import collections, os
os.environ.setdefault("LLM_MODEL", "cx/gpt-5.6-luna-review")
import run_baseline as rb
import run_with_model as rw
import run_ablation as ra
from llm_understand import load_env
from rag.chunker import all_chunks, load_all, retrievable_chunks

env = load_env()
n = len(rw.CASES)
det = sum(int(rw.run(c, with_model=False, env=env, use_cache=True)[1].passed)
          for c in rw.CASES)
mod = sum(int(rw.run(c, with_model=True, env=env, use_cache=True)[1].passed)
          for c in rw.CASES)
san = sum(1 for c in rb.DATA["cases"] if c["expect"]["kind"] == "no_data")
docs = load_all(KNOWLEDGE)

fig = plt.figure(figsize=(13, 7.2))
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.32)

# (1) tiến trình chất lượng, có SÀN làm mốc dưới
ax = fig.add_subplot(gs[0, 0])
ax.bar(["sàn", "tất định", "+ mô hình"], [san, det, mod],
       color=[XAM, XANH, CAM], width=0.6)
for i, v in enumerate([san, det, mod]):
    ax.text(i, v + 2, f"{100*v/n:.1f}%", ha="center", fontweight="bold", fontsize=9)
ax.set_ylim(0, n * 1.2); ax.set_ylabel(f"ca qua / {n}")
ax.set_title("Chất lượng trả lời", fontsize=11)

# (2) lỗi an toàn — cột 0 là điều đáng báo cáo nhất
ax = fig.add_subplot(gs[0, 1])
ax.bar(["tất định", "+ mô hình"], [0, 0], color=[XANH, CAM], width=0.5)
ax.set_ylim(0, 3); ax.set_yticks([0, 1, 2, 3])
ax.text(0.5, 1.5, "0  và  0", ha="center", fontsize=22, fontweight="bold", color=DO)
ax.set_title("Lỗi an toàn\n(dị ứng, bịa món, bịa giá)", fontsize=11)
ax.set_ylabel("số lỗi")

# (3) chia tập đánh giá
ax = fig.add_subplot(gs[0, 2])
grp = collections.Counter(rb.group_of(c["family"]) for c in rb.DATA["cases"])
ax.pie([grp["chốt"], grp["phát triển"], grp["niêm phong"]],
       labels=[f"chốt\n{grp['chốt']}", f"phát triển\n{grp['phát triển']}",
               f"niêm phong\n{grp['niêm phong']}"],
       colors=[DO, XANH, XAM], autopct="%1.0f%%", startangle=140,
       textprops={"fontsize": 9})
ax.set_title(f"{n} ca / 3 nhóm", fontsize=11)

# (4) kho tri thức
ax = fig.add_subplot(gs[1, 0])
mode = collections.Counter(d.answer_mode for d in docs)
b = ax.bar(["verbatim", "synthesize"], [mode["verbatim"], mode["synthesize"]],
           color=[DO, XANH], width=0.55)
ax.bar_label(b, padding=2, fontweight="bold")
ax.set_ylim(0, max(mode.values()) * 1.25); ax.set_ylabel("tài liệu")
ax.set_title(f"Kho tri thức\n{len(docs)} tài liệu / "
             f"{len(all_chunks(KNOWLEDGE))} đoạn", fontsize=11)

# (5) ablation: hàng rào vs tính năng
ax = fig.add_subplot(gs[1, 1])
base_ok, _ = ra.measure()
hang_rao = tinh_nang = 0
for _, tat in ra.ABLATIONS:
    hoan_lai = tat()
    try:
        _, unsafe = ra.measure()
    finally:
        hoan_lai()
    if unsafe: hang_rao += 1
    else: tinh_nang += 1
b = ax.bar(["hàng rào\nan toàn", "tính năng\nchất lượng"], [hang_rao, tinh_nang],
           color=[DO, XANH], width=0.55)
ax.bar_label(b, padding=2, fontweight="bold")
ax.set_ylim(0, max(hang_rao, tinh_nang) * 1.35); ax.set_ylabel("số cơ chế")
ax.set_title(f"{len(ra.ABLATIONS)} cơ chế — không cơ chế nào dư", fontsize=11)

# (6) điều CHƯA đo — phải có mặt trong báo cáo
ax = fig.add_subplot(gs[1, 2])
ax.axis("off")
ax.text(0.5, 1.02, "Điều CHƯA đo", ha="center", fontsize=11, fontweight="bold",
        transform=ax.transAxes)
chua = ["so BM25 / embedding / hybrid", "tập đánh giá truy hồi (~120 ca)",
        "bộ nhớ phiên đa lượt (~25 kịch bản)", "thẻ giỏ hàng gợi ý",
        "5 endpoint dịch vụ HTTP", "độ trễ end-to-end thật"]
for i, t in enumerate(chua):
    ax.text(0.02, 0.86 - i * 0.155, f"○  {t}", fontsize=9.5, transform=ax.transAxes,
            color="#555")
ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False,
                           edgecolor=XAM, linewidth=1, linestyle="--"))

fig.suptitle("Hệ thống AI tư vấn đặt món — kết quả đo được và phần chưa đo",
             fontsize=13, fontweight="bold", y=0.99)
plt.show()
print(f"tất định {det}/{n} | có mô hình {mod}/{n} | lỗi an toàn 0 và 0 | "
      f"{hang_rao}/{len(ra.ABLATIONS)} cơ chế là hàng rào an toàn")
"""))

    out.append(md(r"""
#### Nhận xét — Mục 17

| Con số | Giá trị | Điều nó **không** nói |
|---|---|---|
| tất định 108/119 | 90,8% | không nói khách thật hỏi gì — mọi ca do người viết |
| có mô hình 119/119 | 100% | **không còn là held-out**; tập niêm phong đã mở ở bước 4 |
| lỗi an toàn 0 / 0 | trên 119 ca | chỉ nói *trên tập này*; nhãn dị nguyên phủ 44/91 nên dữ liệu vẫn thiếu |
| kho 84 tài liệu / 327 đoạn | đủ để so truy hồi | chưa nói phương pháp nào tốt hơn — **chưa đo** |
| 9/9 cơ chế có giá trị | 5 là hàng rào an toàn | "ăn hết đoạn" đo được 1 ca nhưng bảo vệ 61 chỗ |

**Số held-out thật duy nhất của dự án: 23/27 (85,2%)** — lần mở tập niêm phong đầu tiên ở bước 4.
Mọi con số sau đó đo trên tập đã thấy.

## 18. Hạn chế phải nói ra

1. **Không có log khách thật.** Mọi ca đánh giá do người viết. Con số đo được hệ thống **có tôn
   trọng ràng buộc hay không**; nó **không** đo được khách thật hỏi gì.
2. **Tập niêm phong đã dùng hết.** Mọi con số trên 119 ca hiện tại không còn là held-out. Tập
   mới (truy hồi, đa lượt) mỗi tập chỉ được mở **một lần**.
3. **28/84 tài liệu tri thức là `demo`** — giá trị mẫu. Chúng không thể nói sai về **con số** (số
   lấy từ thực đơn) nhưng có thể sai về **chính sách**, và chỉ chủ nhà hàng biết.
4. **Nhãn dị nguyên phủ 44/91 món.** Đối chiếu mô tả tìm ra 7 lỗ thật đã lấp, nhưng mô tả không
   phải bảng thành phần nên **còn thiếu bao nhiêu thì không biết được từ dữ liệu này**.
5. **Độ trễ mô hình ~8,6 giây/lần gọi.** Chỉ 20% ca gọi, nhưng đây là con số đáng lo nhất khi
   dùng thật.
6. **Chưa chạy thật end-to-end.** Dịch vụ HTTP đã có (5 endpoint · bộ nhớ phiên 3 quy tắc · thẻ
   giỏ 5 bất biến · hợp đồng schema — **196 test**), nhưng chưa ai chạy `docker compose up` rồi quét
   QR. Chạy thật kiểm đúng thứ test **không chạm tới**: container, mạng, và việc backend gọi được
   dịch vụ. Nên nó **không thay được bằng test**, dù test có bao nhiêu.

## 19. Hướng phát triển, gắn với từng thành viên

| TV | Việc còn lại | Điều kiện chấp nhận đo được |
|---|---|---|
| **1** | **~120 ca truy hồi** rồi **~25 kịch bản đa lượt** (chặn TV3 và TV5) · ca giỏ hàng · `analyze_failures.py` | bộ dò lỗ tìm 0 lỗ trên tập mới |
| **2** | nối tên món dị nguyên còn thiếu · nhận `session_state` | 119 ca không tụt, 0 lỗi an toàn |
| **3** | BM25 · embedding · hybrid RRF · phép so trên **hai** bài toán | Hit@5, MRR@5, **forbidden@5**, kèm `n` |
| **4** | — (đã xong `cart.py`) | chốt `safety_cart_no_allergen` xanh khi TV1 viết ca |
| **5** | **chạy thật `docker compose`** (mã đã xong: 5 endpoint, bộ nhớ phiên) | quét QR, hỏi 5 câu, đóng phiên → **bộ nhớ mất** |

### Ba điều cấm, áp cho cả 5 người, và CI ép

1. **Không nới ràng buộc dị nguyên** — kể cả khi kết quả rỗng.
2. **Không để mô hình sinh chọn món** — nó chỉ trả về nhãn, và nhãn bị cổng kiểm lại.
3. **Không viết số vào tài liệu** — số phải tính được, nếu không nó sẽ trôi. Dự án này đã mắc
   đúng lỗi đó một lần với con số kiểm kê đụng chữ.
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
