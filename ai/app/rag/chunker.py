# -*- coding: utf-8 -*-
"""Đọc tài liệu tri thức và chia thành đoạn cho bộ truy hồi.

Vì sao cần chia đoạn
--------------------
Hệ thống có HAI lớp tri thức, và ranh giới giữa chúng là quyết định quan trọng nhất của tệp
này. Ranh giới đó **không phải** "tra khóa vs truy hồi xếp hạng" — cả 60 tài liệu ở lớp 2 đều
có đúng một `topic_keys`, nên lớp 2 cũng tra khóa được. Ranh giới thật là **chế độ trả lời**:

    Lớp 1 — restaurant-facts.json : trả NGUYÊN VĂN. Mô hình không chạm vào chữ.
    Lớp 2 — ai/knowledge/*.md     : là ĐẦU VÀO cho mô hình viết câu trả lời.

Vì sao phải hai chế độ chứ không một:

- Gộp tất cả về lớp 2 → "mấy giờ đóng cửa" sẽ do mô hình viết, và nó **có thể** viết 22h30.
  Giờ đóng cửa, giá, và nhãn dị nguyên là loại thông tin **không được phép diễn đạt lại**. Mất
  bảo đảm không-bóp-méo mà không được gì.
- Gộp tất cả về lớp 1 → phải nén "món miền Trung có gì đặc trưng" vào một câu nguyên văn viết
  tay, nhưng câu trả lời thật là danh sách nhiều món kèm ghi chú dị nguyên. Nén là mất nội
  dung, và mất luôn khả năng trả lời loại câu hỏi nhiều mặt.

Số **kho lưu trữ** thì gộp được (đưa 24 chủ đề vào markdown kèm `answer_mode: verbatim` là một
cải tiến gọn gàng hợp lệ). Số **chế độ trả lời** thì không, vì nó là chuyện an toàn.

Hệ quả phải canh: `answer.py` tra lớp 1 **trước**, nên một chủ đề có ở cả hai lớp thì tài liệu
lớp 2 không bao giờ tới lượt mà vẫn chiếm chỗ trong chỉ mục. Bất biến rời-nhau được ép trong
`test_chunker.HaiKhoTriThucKhongDuocTRUNGCHUDE`.

Ba quy tắc chia đoạn
--------------------
1. **Chia theo heading `##`.** Người viết đã chia ý bằng heading, nên chia theo heading là chia
   theo ý nghĩa. Chia theo số ký tự thì cắt giữa câu.

2. **Kèm tiêu đề tài liệu vào mỗi đoạn.** Đoạn bị trích ra khỏi tài liệu phải tự đủ nghĩa.
   Đoạn "Có 11 món, phần lớn ở nhóm Món gà." không nói được nó nói về cái gì; thêm tiêu đề
   "Món nướng" vào thì nói được.

3. **`chunk_id` tất định**: `{doc_id}#{index}`. Nhờ vậy tập đánh giá truy hồi trỏ vào đoạn cụ
   thể được, và trỏ đó không đổi khi sinh lại.

Vì sao `audience: guest` bị ép chặt
-----------------------------------
Bản cũ có 27 tài liệu tri thức, và **5 trong đó mang `audience: ai`** — chúng là hướng dẫn cho
AI đọc: phong cách trả lời, ví dụ phản hồi sai, hướng dẫn phân biệt ngữ cảnh. Cả 27 tài liệu
bị chặt vào **cùng một chỉ mục truy hồi**, nên bộ truy hồi trích được đoạn hướng dẫn nội bộ ra
cho khách đọc. **47/221 đoạn** đã bị trích như vậy, nhiều tháng không ai phát hiện.

Nên bộ nạp này **TỪ CHỐI** tệp không phải `audience: guest`, chứ không lọc bỏ. Khác biệt quan
trọng: lọc thì người ta vẫn thêm được tệp nội bộ vào thư mục và nó chỉ im lặng bị bỏ qua; từ
chối thì việc thêm bị chặn ngay, kèm thông báo lý do.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Đoạn dài hơn ngưỡng này bị chia tiếp theo heading `###`. Ngưỡng tính bằng TỪ, không phải ký
# tự, vì tiếng Việt có dấu nên đếm ký tự lệch nhiều so với lượng thông tin.
MAX_WORDS_PER_CHUNK = 400

# Đoạn ngắn hơn ngưỡng này bị GỘP vào đoạn liền sau, không phát ra thành đoạn riêng.
#
# Vì sao cần: nhiều tài liệu mở đầu bằng `# Tiêu đề` rồi vào ngay `## Mục đầu tiên`. Phần trước
# heading đầu khi đó chỉ có dòng tiêu đề — một "đoạn" như vậy không mang tín hiệu nào để truy
# hồi, nhưng vẫn chiếm một chỗ trong top-k và đẩy một đoạn có ích ra ngoài.
#
# Gộp thay vì bỏ, vì dòng tiêu đề vẫn là ngữ cảnh có ích cho đoạn sau nó.
MIN_WORDS_PER_CHUNK = 12

ALLOWED_AUDIENCE = "guest"
ALLOWED_SOURCES = ("derived", "demo", "restaurant")


class KnowledgeError(ValueError):
    """Tài liệu tri thức viết sai. Là lỗi nội dung, không phải lỗi hệ thống."""


@dataclass(frozen=True)
class KnowledgeChunk:
    """Một đoạn tri thức, tự đủ nghĩa khi bị trích rời khỏi tài liệu."""

    chunk_id: str          # "{doc_id}#{index}" — tất định
    doc_id: str
    title: str             # tiêu đề tài liệu
    heading: str           # tiêu đề mục, "" nếu là đoạn mở đầu
    topic_keys: tuple[str, ...]
    source: str            # derived | demo | restaurant
    text: str              # đã kèm tiêu đề tài liệu

    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass
class KnowledgeDoc:
    doc_id: str
    title: str
    topic_keys: tuple[str, ...]
    source: str
    path: Path
    body: str
    chunks: list[KnowledgeChunk] = field(default_factory=list)


_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    """Tách frontmatter YAML tối giản khỏi phần thân.

    Chỉ đọc `khóa: giá trị` một dòng và danh sách dạng `[a, b]` — không dùng thư viện YAML,
    vì kho tri thức chỉ cần đúng bốn khóa và thêm một phụ thuộc cho việc đó là quá đắt.
    """
    match = _FRONTMATTER.match(text)
    if match is None:
        raise KnowledgeError(f"{path.name}: thiếu frontmatter `---` ở đầu tệp")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise KnowledgeError(f"{path.name}: dòng frontmatter không có dấu hai chấm: {line!r}")
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, text[match.end():]


def load_doc(path: Path) -> KnowledgeDoc:
    text = path.read_text(encoding="utf-8-sig")
    meta, body = parse_frontmatter(text, path)

    for required in ("id", "title", "source", "audience"):
        if not meta.get(required):
            raise KnowledgeError(f"{path.name}: thiếu khóa frontmatter bắt buộc `{required}`")

    # TỪ CHỐI, không lọc. Xem docstring đầu tệp: bản cũ trộn hướng dẫn cho AI vào cùng chỉ mục
    # truy hồi và 47/221 đoạn bị trích cho khách đọc.
    if meta["audience"] != ALLOWED_AUDIENCE:
        raise KnowledgeError(
            f"{path.name}: audience={meta['audience']!r} bị từ chối. Kho tri thức chỉ nhận "
            f"`audience: {ALLOWED_AUDIENCE}` — nội dung dành cho AI đọc (phong cách trả lời, "
            "ví dụ phản hồi sai) KHÔNG được nằm ở đây, vì bộ truy hồi sẽ trích nó cho khách."
        )
    if meta["source"] not in ALLOWED_SOURCES:
        raise KnowledgeError(
            f"{path.name}: source={meta['source']!r} không hợp lệ, phải là một trong "
            f"{ALLOWED_SOURCES}"
        )

    raw_keys = meta.get("topic_keys", "").strip().strip("[]")
    keys = tuple(k.strip() for k in raw_keys.split(",") if k.strip())

    doc = KnowledgeDoc(
        doc_id=meta["id"],
        title=meta["title"],
        topic_keys=keys,
        source=meta["source"],
        path=path,
        body=body,
    )
    doc.chunks = chunk_doc(doc)
    return doc


def _split_sections(body: str) -> list[tuple[str, str]]:
    """(tiêu đề mục, nội dung) theo heading `##`. Đoạn trước heading đầu có tiêu đề rỗng."""
    parts: list[tuple[str, str]] = []
    current_heading = ""
    buffer: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(buffer).strip():
                parts.append((current_heading, "\n".join(buffer).strip()))
            current_heading = line[3:].strip()
            buffer = []
        else:
            buffer.append(line)
    if "".join(buffer).strip():
        parts.append((current_heading, "\n".join(buffer).strip()))
    return parts


def _split_long(heading: str, text: str) -> list[tuple[str, str]]:
    """Mục quá dài thì chia tiếp theo `###`; vẫn dài thì chia theo đoạn văn."""
    if len(text.split()) <= MAX_WORDS_PER_CHUNK:
        return [(heading, text)]

    subs: list[tuple[str, str]] = []
    sub_heading = heading
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("### "):
            if "".join(buffer).strip():
                subs.append((sub_heading, "\n".join(buffer).strip()))
            sub_heading = f"{heading} — {line[4:].strip()}"
            buffer = []
        else:
            buffer.append(line)
    if "".join(buffer).strip():
        subs.append((sub_heading, "\n".join(buffer).strip()))

    # Vẫn còn mục dài sau khi chia theo `###` thì cắt theo đoạn văn — thà đoạn hơi dài còn
    # hơn cắt giữa câu.
    out: list[tuple[str, str]] = []
    for head, chunk_text in subs:
        if len(chunk_text.split()) <= MAX_WORDS_PER_CHUNK:
            out.append((head, chunk_text))
            continue
        paragraphs = [p.strip() for p in chunk_text.split("\n\n") if p.strip()]
        acc: list[str] = []
        for para in paragraphs:
            acc.append(para)
            if len(" ".join(acc).split()) >= MAX_WORDS_PER_CHUNK:
                out.append((head, "\n\n".join(acc)))
                acc = []
        if acc:
            out.append((head, "\n\n".join(acc)))
    return out


def _merge_short(pieces: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Gộp mảnh quá ngắn vào mảnh liền sau (hoặc liền trước nếu nó là mảnh cuối).

    Chạy TRƯỚC khi cấp `chunk_id`, để mã đoạn vẫn liên tục 0,1,2... Nếu gộp sau khi cấp mã thì
    dãy mã bị khuyết và tập đánh giá truy hồi trỏ vào mã không tồn tại.
    """
    if len(pieces) <= 1:
        return pieces
    out: list[tuple[str, str]] = []
    carry: tuple[str, str] | None = None
    for heading, text in pieces:
        if carry is not None:
            heading = carry[0] or heading
            text = f"{carry[1]}\n\n{text}"
            carry = None
        if len(text.split()) < MIN_WORDS_PER_CHUNK:
            carry = (heading, text)
            continue
        out.append((heading, text))
    if carry is not None:
        if out:
            last_heading, last_text = out[-1]
            out[-1] = (last_heading, f"{last_text}\n\n{carry[1]}")
        else:
            out.append(carry)
    return out


def chunk_doc(doc: KnowledgeDoc) -> list[KnowledgeChunk]:
    pieces: list[tuple[str, str]] = []
    for heading, text in _split_sections(doc.body):
        pieces.extend(_split_long(heading, text))

    chunks: list[KnowledgeChunk] = []
    for index, (heading, text) in enumerate(_merge_short(pieces)):
        # Quy tắc 2: kèm tiêu đề tài liệu, để đoạn tự đủ nghĩa khi trích rời.
        prefix = doc.title if not heading else f"{doc.title} — {heading}"
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"{doc.doc_id}#{index}",
                doc_id=doc.doc_id,
                title=doc.title,
                heading=heading,
                topic_keys=doc.topic_keys,
                source=doc.source,
                text=f"{prefix}\n{text}",
            )
        )
    if not chunks:
        raise KnowledgeError(f"{doc.path.name}: tài liệu không có nội dung nào để chia đoạn")
    return chunks


def load_all(root: Path) -> list[KnowledgeDoc]:
    """Nạp mọi tài liệu trong `root`, sắp theo `doc_id` để thứ tự đoạn tất định."""
    docs = [load_doc(p) for p in sorted(root.rglob("*.md"))]
    seen: dict[str, Path] = {}
    for doc in docs:
        if doc.doc_id in seen:
            raise KnowledgeError(
                f"{doc.path.name}: id {doc.doc_id!r} trùng với {seen[doc.doc_id].name}"
            )
        seen[doc.doc_id] = doc.path
    return sorted(docs, key=lambda d: d.doc_id)


def all_chunks(root: Path) -> list[KnowledgeChunk]:
    return [c for doc in load_all(root) for c in doc.chunks]
