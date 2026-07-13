// Thesis defense deck — "Xây dựng Chatbot đặt món nhà hàng dùng LLM và RAG"
// Course: Học máy & Khai phá dữ liệu. ~12 slides, 10-min defense. CMC brand.
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 in
p.author = "CMC University";
p.title = "Chatbot đặt món nhà hàng — LLM & RAG";

const C = {
  ink: "08233E", primary: "005BAC", primary2: "0067C7", cyan: "08BCEF",
  teal: "00A99D", green: "00A86B", soft: "F2FAFD", soft2: "EAF7FC",
  border: "CFEAF5", muted: "667A91", danger: "B42318", white: "FFFFFF", amber: "B8860B",
};
const F = "Segoe UI";
const W = 13.3, H = 7.5, M = 0.6;
const shadow = () => ({ type: "outer", color: "08233E", blur: 9, offset: 3, angle: 135, opacity: 0.12 });

function slideBase(dark = false) {
  const s = p.addSlide();
  s.background = { color: dark ? C.ink : C.white };
  return s;
}
function kicker(s, t, color = C.primary) {
  s.addText(t.toUpperCase(), { x: M, y: 0.42, w: W - 2 * M, h: 0.32, fontFace: F, fontSize: 12.5, bold: true, color, charSpacing: 2.5, margin: 0 });
}
function title(s, t, color = C.ink) {
  s.addText(t, { x: M, y: 0.72, w: W - 2 * M, h: 0.82, fontFace: F, fontSize: 29, bold: true, color, margin: 0 });
}
function pageNum(s, n) {
  s.addText(String(n).padStart(2, "0") + " / 12", { x: W - 1.7, y: H - 0.5, w: 1.1, h: 0.3, fontFace: F, fontSize: 10, color: C.muted, align: "right", margin: 0 });
}
// card with left accent bar
function card(s, x, y, w, h, accent, fill = C.soft) {
  s.addShape(p.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: C.border, width: 1 }, shadow: shadow() });
  if (accent) s.addShape(p.shapes.RECTANGLE, { x, y, w: 0.09, h, fill: { color: accent }, line: { type: "none" } });
}
function badge(s, x, y, n, color) {
  s.addShape(p.shapes.OVAL, { x, y, w: 0.52, h: 0.52, fill: { color }, line: { type: "none" } });
  s.addText(String(n), { x, y, w: 0.52, h: 0.52, fontFace: F, fontSize: 18, bold: true, color: C.white, align: "center", valign: "middle", margin: 0 });
}

// ───────────────────────── Slide 1 — Title ─────────────────────────
(() => {
  const s = slideBase(true);
  // motif accents
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.primary }, line: { type: "none" } });
  s.addShape(p.shapes.OVAL, { x: W - 2.7, y: -1.3, w: 3.4, h: 3.4, fill: { color: C.primary2, transparency: 78 }, line: { type: "none" } });
  s.addShape(p.shapes.OVAL, { x: W - 1.7, y: H - 1.9, w: 2.8, h: 2.8, fill: { color: C.cyan, transparency: 82 }, line: { type: "none" } });

  kicker(s, "Đồ án môn học · Học máy & Khai phá dữ liệu", C.cyan);
  s.addText("Xây dựng Chatbot đặt món nhà hàng\nứng dụng LLM và RAG", {
    x: M, y: 1.5, w: 11.4, h: 2.0, fontFace: F, fontSize: 40, bold: true, color: C.white, lineSpacingMultiple: 1.02, margin: 0,
  });
  s.addText("Building a Restaurant Food-Ordering Chatbot using LLM and RAG", {
    x: M, y: 3.55, w: 11.0, h: 0.45, fontFace: F, fontSize: 16, italic: true, color: C.cyan, margin: 0,
  });
  s.addShape(p.shapes.LINE, { x: M, y: 4.35, w: 4.3, h: 0, line: { color: C.teal, width: 2.5 } });
  s.addText([
    { text: "Sinh viên thực hiện:  ", options: { bold: true, color: C.white } },
    { text: "[Họ và tên] — [MSSV]", options: { color: "CADCFC" } },
  ], { x: M, y: 4.7, w: 11, h: 0.4, fontFace: F, fontSize: 15, margin: 0 });
  s.addText([
    { text: "Giảng viên hướng dẫn:  ", options: { bold: true, color: C.white } },
    { text: "[Tên giảng viên]", options: { color: "CADCFC" } },
  ], { x: M, y: 5.15, w: 11, h: 0.4, fontFace: F, fontSize: 15, margin: 0 });
  s.addText([
    { text: "Lớp / Khóa:  ", options: { bold: true, color: C.white } },
    { text: "[Lớp]", options: { color: "CADCFC" } },
  ], { x: M, y: 5.6, w: 11, h: 0.4, fontFace: F, fontSize: 15, margin: 0 });
  s.addText("CMC University · Tháng 6, 2026", { x: M, y: 6.5, w: 11, h: 0.4, fontFace: F, fontSize: 13, color: C.muted, margin: 0 });
})();

// ───────────────────────── Slide 2 — Vấn đề & Mục tiêu ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Giới thiệu");
  title(s, "Đặt vấn đề & Mục tiêu");
  const y = 1.85, h = 4.9, w = 5.85;
  // problem
  card(s, M, y, w, h, C.primary);
  s.addText("Bối cảnh & Vấn đề", { x: M + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.primary, margin: 0 });
  s.addText([
    { text: "Nhà hàng dùng QR gọi món; khách hỏi rất nhiều: menu, combo, dị ứng, giờ mở cửa, thanh toán.", options: { bullet: true, breakLine: true } },
    { text: "Nhân viên quá tải, trả lời chậm và thiếu nhất quán.", options: { bullet: true, breakLine: true } },
    { text: "Chatbot ngây thơ dễ bịa giá / bịa món, thậm chí tự đặt đơn — rủi ro vận hành.", options: { bullet: true, breakLine: true } },
    { text: "Cần trợ lý AI bám sát dữ liệu thật, an toàn và đo lường được.", options: { bullet: true } },
  ], { x: M + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14.5, color: C.ink, paraSpaceAfter: 10, lineSpacingMultiple: 1.0, margin: 0 });
  // objectives
  const x2 = M + w + 0.4;
  card(s, x2, y, w, h, C.teal);
  s.addText("Mục tiêu đồ án", { x: x2 + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.teal, margin: 0 });
  s.addText([
    { text: "Chatbot RAG trả lời dựa trên kho tri thức (KB) của nhà hàng, có trích nguồn.", options: { bullet: true, breakLine: true } },
    { text: "An toàn AI: guardrails chặn bịa giá/món, AI không bao giờ tự đặt đơn.", options: { bullet: true, breakLine: true } },
    { text: "Đánh giá định lượng bằng bộ câu hỏi chuẩn (golden questions).", options: { bullet: true, breakLine: true } },
    { text: "Tích hợp vào hệ thống thật: React + .NET + dịch vụ AI (Python).", options: { bullet: true } },
  ], { x: x2 + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14.5, color: C.ink, paraSpaceAfter: 10, margin: 0 });
  pageNum(s, 2);
})();

// ───────────────────────── Slide 3 — Góc nhìn ML & KPDL ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Khung lý thuyết");
  title(s, "Góc nhìn Học máy & Khai phá dữ liệu");
  const cards = [
    ["1", C.primary, "Truy xuất thông tin (IR)", "Okapi BM25 xếp hạng đoạn văn bản liên quan theo TF–IDF; nền tảng của bước Retrieval."],
    ["2", C.teal, "Khai phá dữ liệu văn bản", "Tách tài liệu thành chunk, trọng số term; luật kết hợp gợi ý cặp món (combo)."],
    ["3", C.cyan, "Mô hình ngôn ngữ (LLM)", "Kiến trúc Transformer sinh câu trả lời tự nhiên từ ngữ cảnh đã truy xuất."],
    ["4", C.green, "Đánh giá mô hình", "Golden set + các chỉ số hit-rate, accuracy, pass-rate để đo chất lượng khách quan."],
  ];
  const w = 5.85, h = 2.3, gx = M, gx2 = M + w + 0.4, gy = 1.85, gy2 = 1.85 + h + 0.3;
  const pos = [[gx, gy], [gx2, gy], [gx, gy2], [gx2, gy2]];
  cards.forEach((c, i) => {
    const [x, y] = pos[i];
    card(s, x, y, w, h, c[1]);
    badge(s, x + 0.3, y + 0.32, c[0], c[1]);
    s.addText(c[2], { x: x + 1.0, y: y + 0.32, w: w - 1.25, h: 0.55, fontFace: F, fontSize: 16.5, bold: true, color: C.ink, valign: "middle", margin: 0 });
    s.addText(c[3], { x: x + 0.3, y: y + 1.05, w: w - 0.6, h: h - 1.2, fontFace: F, fontSize: 13.5, color: C.muted, lineSpacingMultiple: 1.02, margin: 0 });
  });
  pageNum(s, 3);
})();

// ───────────────────────── Slide 4 — Phương pháp & Lựa chọn ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Phương pháp");
  title(s, "Lựa chọn kỹ thuật & Đánh đổi");
  const y = 1.85, h = 4.9, w = 5.85;
  // RAG vs Fine-tune
  card(s, M, y, w, h, C.primary);
  s.addText("RAG  vs  Fine-tuning", { x: M + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.primary, margin: 0 });
  s.addText([
    { text: "✓  Chọn RAG", options: { bold: true, color: C.green, breakLine: true } },
    { text: "Cập nhật KB tức thì, không cần huấn luyện lại.", options: { bullet: true, breakLine: true } },
    { text: "Trích dẫn nguồn → minh bạch, chống bịa đặt.", options: { bullet: true, breakLine: true } },
    { text: "Rẻ, không cần GPU; phù hợp dữ liệu nhà hàng hay đổi.", options: { bullet: true, breakLine: true } },
    { text: "✗  Fine-tuning: tốn dữ liệu + GPU, khó cập nhật, dễ \"học vẹt\".", options: { color: C.muted } },
  ], { x: M + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14, color: C.ink, paraSpaceAfter: 9, margin: 0 });
  // BM25 vs Embeddings
  const x2 = M + w + 0.4;
  card(s, x2, y, w, h, C.teal);
  s.addText("BM25  vs  Embeddings", { x: x2 + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.teal, margin: 0 });
  s.addText([
    { text: "✓  Chọn BM25 (Okapi)", options: { bold: true, color: C.green, breakLine: true } },
    { text: "KB nhỏ (35 chunk) → thống kê từ khóa đã đủ chính xác.", options: { bullet: true, breakLine: true } },
    { text: "Không cần model embedding / vector DB / GPU.", options: { bullet: true, breakLine: true } },
    { text: "Minh bạch, dễ giải thích; tiếng Việt ổn nhờ chuẩn hóa bỏ dấu.", options: { bullet: true, breakLine: true } },
    { text: "✗  Embeddings: nặng hạ tầng, lợi ích nhỏ ở quy mô KB này.", options: { color: C.muted } },
  ], { x: x2 + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14, color: C.ink, paraSpaceAfter: 9, margin: 0 });
  pageNum(s, 4);
})();

// ───────────────────────── Slide 5 — Kiến trúc hệ thống ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Kiến trúc");
  title(s, "Kiến trúc hệ thống");
  const boxes = [
    ["Khách hàng", "Giao diện chat\nReact (QR)", C.primary],
    ["Backend", ".NET API\nxác thực đơn", C.ink],
    ["Dịch vụ AI", "RAG + LLM\n(Python)", C.teal],
    ["Knowledge Base", "7 tài liệu\n35 chunks", C.green],
  ];
  const bw = 2.7, bh = 1.7, gap = 0.42, y = 2.75;
  let x = 0.75;
  const centers = [];
  boxes.forEach((b, i) => {
    card(s, x, y, bw, bh, b[2], C.white);
    s.addText(b[0], { x: x + 0.15, y: y + 0.22, w: bw - 0.3, h: 0.4, fontFace: F, fontSize: 15.5, bold: true, color: b[2], align: "center", margin: 0 });
    s.addText(b[1], { x: x + 0.15, y: y + 0.72, w: bw - 0.3, h: 0.85, fontFace: F, fontSize: 12.5, color: C.muted, align: "center", lineSpacingMultiple: 1.0, margin: 0 });
    centers.push(x + bw);
    if (i < boxes.length - 1) {
      s.addShape(p.shapes.LINE, { x: x + bw + 0.04, y: y + bh / 2, w: gap - 0.08, h: 0, line: { color: C.primary, width: 2.5, endArrowType: "triangle" } });
    }
    x += bw + gap;
  });
  // Gemini API below AI service
  const aiX = 0.75 + 2 * (bw + gap); // start x of 3rd box
  card(s, aiX, y + bh + 0.7, bw, 1.0, C.cyan, C.soft2);
  s.addText("Gemini 3.5 Flash", { x: aiX + 0.1, y: y + bh + 0.82, w: bw - 0.2, h: 0.4, fontFace: F, fontSize: 14, bold: true, color: C.primary, align: "center", margin: 0 });
  s.addText("Google API chính thức", { x: aiX + 0.1, y: y + bh + 1.2, w: bw - 0.2, h: 0.35, fontFace: F, fontSize: 11, color: C.muted, align: "center", margin: 0 });
  s.addShape(p.shapes.LINE, { x: aiX + bw / 2, y: y + bh + 0.04, w: 0, h: 0.62, line: { color: C.teal, width: 2.5, endArrowType: "triangle", beginArrowType: "triangle" } });
  // caption
  s.addText("Pipeline mỗi câu hỏi:  Guardrails đầu vào  →  BM25 truy xuất (top-k=5)  →  Dựng prompt  →  LLM sinh JSON  →  Output Parser kiểm duyệt  →  Trả gợi ý (khách xác nhận).", {
    x: M, y: 6.45, w: W - 2 * M, h: 0.6, fontFace: F, fontSize: 12.5, italic: true, color: C.ink, align: "center", margin: 0,
  });
  pageNum(s, 5);
})();

// ───────────────────────── Slide 6 — KB + BM25 ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Truy xuất");
  title(s, "Knowledge Base & BM25 Retriever");
  const y = 1.85, h = 4.9;
  // KB stats left
  const w1 = 5.3;
  card(s, M, y, w1, h, C.primary);
  s.addText("Kho tri thức (KB)", { x: M + 0.3, y: y + 0.25, w: w1 - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.primary, margin: 0 });
  // big stats
  s.addText([{ text: "7", options: { fontSize: 54, bold: true, color: C.primary } }, { text: "  tài liệu .md", options: { fontSize: 16, color: C.ink } }],
    { x: M + 0.35, y: y + 0.9, w: w1 - 0.6, h: 0.9, fontFace: F, valign: "middle", margin: 0 });
  s.addText([{ text: "35", options: { fontSize: 54, bold: true, color: C.teal } }, { text: "  chunks", options: { fontSize: 16, color: C.ink } }],
    { x: M + 0.35, y: y + 1.85, w: w1 - 0.6, h: 0.9, fontFace: F, valign: "middle", margin: 0 });
  s.addText([
    { text: "Nội dung: menu, combo, chính sách đặt món, dị ứng, FAQ…", options: { bullet: true, breakLine: true } },
    { text: "Mỗi chunk có title + tag để tăng độ chính xác truy xuất.", options: { bullet: true } },
  ], { x: M + 0.35, y: y + 2.95, w: w1 - 0.65, h: 1.7, fontFace: F, fontSize: 13.5, color: C.muted, paraSpaceAfter: 9, margin: 0 });
  // BM25 right
  const x2 = M + w1 + 0.4, w2 = 6.4;
  card(s, x2, y, w2, h, C.teal);
  s.addText("Okapi BM25 — tham số", { x: x2 + 0.3, y: y + 0.25, w: w2 - 0.5, h: 0.45, fontFace: F, fontSize: 18, bold: true, color: C.teal, margin: 0 });
  const rows = [
    ["k1 = 1.5", "độ bão hòa tần suất từ"],
    ["b = 0.75", "chuẩn hóa theo độ dài đoạn"],
    ["TITLE_BOOST × 1.5", "ưu tiên khớp ở tiêu đề"],
    ["TAG_BOOST × 1.0", "khớp theo nhãn chủ đề"],
    ["top_k = 5", "số đoạn đưa vào ngữ cảnh"],
  ];
  let ry = y + 0.95;
  rows.forEach((r) => {
    s.addShape(p.shapes.RECTANGLE, { x: x2 + 0.3, y: ry, w: 2.55, h: 0.55, fill: { color: C.soft2 }, line: { color: C.border, width: 1 } });
    s.addText(r[0], { x: x2 + 0.3, y: ry, w: 2.55, h: 0.55, fontFace: F, fontSize: 14, bold: true, color: C.primary, align: "center", valign: "middle", margin: 0 });
    s.addText(r[1], { x: x2 + 3.0, y: ry, w: w2 - 3.2, h: 0.5, fontFace: F, fontSize: 13, color: C.ink, valign: "middle", margin: 0 });
    ry += 0.64;
  });
  s.addText("Chuẩn hóa tiếng Việt (bỏ dấu, lowercase) trước khi đánh chỉ mục → khớp bền vững với cách gõ của khách.", {
    x: x2 + 0.3, y: ry + 0.04, w: w2 - 0.6, h: 0.6, fontFace: F, fontSize: 12, italic: true, color: C.muted, margin: 0,
  });
  pageNum(s, 6);
})();

// ───────────────────────── Slide 7 — Guardrails ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "An toàn AI", C.danger);
  title(s, "Guardrails — Hệ thống an toàn");
  const y = 1.8, h = 3.5, w = 5.85;
  // input flags
  card(s, M, y, w, h, C.primary);
  s.addText("5 cờ kiểm soát đầu vào", { x: M + 0.3, y: y + 0.22, w: w - 0.5, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: C.primary, margin: 0 });
  s.addText([
    { text: "CUSTOMER_CONFIRMATION_REQUIRED — ý định đặt đơn", options: { bullet: true, breakLine: true } },
    { text: "PRICE_FABRICATION_BLOCKED — đòi bịa giá", options: { bullet: true, breakLine: true } },
    { text: "MENU_FABRICATION_BLOCKED — đòi món ngoài thực đơn", options: { bullet: true, breakLine: true } },
    { text: "OUT_OF_SCOPE — lạc chủ đề (thời tiết, code…)", options: { bullet: true, breakLine: true } },
    { text: "PROFANITY_DETECTED — ngôn từ xúc phạm", options: { bullet: true } },
  ], { x: M + 0.3, y: y + 0.75, w: w - 0.55, h: h - 0.95, fontFace: F, fontSize: 12.8, color: C.ink, paraSpaceAfter: 7, margin: 0 });
  // system flags
  const x2 = M + w + 0.4;
  card(s, x2, y, w, h, C.amber);
  s.addText("2 cờ hệ thống", { x: x2 + 0.3, y: y + 0.22, w: w - 0.5, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: C.amber, margin: 0 });
  s.addText([
    { text: "AI_OUTPUT_SCHEMA_INVALID — LLM trả sai cấu trúc JSON → chặn cứng đầu ra.", options: { bullet: true, breakLine: true } },
    { text: "AI_PROVIDER_UNAVAILABLE — LLM lỗi/timeout → rơi về chế độ RAG-only an toàn.", options: { bullet: true } },
  ], { x: x2 + 0.3, y: y + 0.75, w: w - 0.55, h: 1.6, fontFace: F, fontSize: 13.2, color: C.ink, paraSpaceAfter: 9, margin: 0 });
  s.addText("Phòng thủ nhiều lớp: input → output → backend đều kiểm tra lại.", {
    x: x2 + 0.3, y: y + 2.7, w: w - 0.6, h: 0.6, fontFace: F, fontSize: 12.5, italic: true, color: C.muted, margin: 0,
  });
  // principle banner
  const by = y + h + 0.35;
  s.addShape(p.shapes.RECTANGLE, { x: M, y: by, w: W - 2 * M, h: 1.0, fill: { color: C.ink }, line: { type: "none" }, shadow: shadow() });
  s.addText([
    { text: "Nguyên tắc cốt lõi:  ", options: { bold: true, color: C.cyan } },
    { text: "AI KHÔNG BAO GIỜ tự đặt đơn.  ", options: { bold: true, color: C.white } },
    { text: "requires_customer_confirmation = true (luôn luôn) — khách phải tự bấm xác nhận.", options: { color: "CADCFC" } },
  ], { x: M + 0.4, y: by, w: W - 2 * M - 0.8, h: 1.0, fontFace: F, fontSize: 14.5, valign: "middle", margin: 0 });
  pageNum(s, 7);
})();

// ───────────────────────── Slide 8 — Output Parser ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Kiểm duyệt đầu ra");
  title(s, "Output Parser — Lọc & xác thực phản hồi LLM");
  const steps = [
    [C.primary, "Trích JSON", "Bóc khối JSON từ phản hồi thô của LLM."],
    [C.teal, "Kiểm tra schema", "suggested_cart_actions phải là list; sai → cờ AI_OUTPUT_SCHEMA_INVALID, chặn."],
    [C.cyan, "Đối chiếu menu", "Chỉ giữ món có ID hợp lệ & còn bán; món bịa bị loại."],
    [C.green, "Chuẩn hóa số lượng", "Clamp quantity về khoảng 1–20, tránh giá trị bất thường."],
    [C.danger, "Ép xác nhận", "Mọi gợi ý đều requires_customer_confirmation = true."],
  ];
  let y = 1.95;
  const rowH = 0.92;
  steps.forEach((st, i) => {
    badge(s, M + 0.05, y + (rowH - 0.52) / 2, i + 1, st[0]);
    s.addShape(p.shapes.RECTANGLE, { x: M + 0.8, y, w: W - 2 * M - 0.8, h: rowH - 0.12, fill: { color: C.soft }, line: { color: C.border, width: 1 } });
    s.addShape(p.shapes.RECTANGLE, { x: M + 0.8, y, w: 0.09, h: rowH - 0.12, fill: { color: st[0] }, line: { type: "none" } });
    s.addText(st[1], { x: M + 1.05, y, w: 3.0, h: rowH - 0.12, fontFace: F, fontSize: 15.5, bold: true, color: C.ink, valign: "middle", margin: 0 });
    s.addText(st[2], { x: M + 4.1, y, w: W - 2 * M - 4.35, h: rowH - 0.12, fontFace: F, fontSize: 13, color: C.muted, valign: "middle", margin: 0 });
    y += rowH;
  });
  s.addText("→ Backend .NET vẫn kiểm tra lại toàn bộ đơn trước khi ghi DB. AI chỉ gợi ý, không có quyền ghi.", {
    x: M, y: y + 0.05, w: W - 2 * M, h: 0.5, fontFace: F, fontSize: 12.5, italic: true, color: C.primary, margin: 0,
  });
  pageNum(s, 8);
})();

// ───────────────────────── Slide 9 — Evaluation ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Đánh giá");
  title(s, "Evaluation — Đo hiệu năng RAG");
  // chart left
  s.addChart(p.charts.BAR, [{ name: "Kết quả", labels: ["Retrieval\nHit@5", "Guardrail\nAccuracy", "Overall\nPass"], values: [78.6, 100.0, 80.0] }], {
    x: M, y: 1.85, w: 7.4, h: 4.8, barDir: "col",
    chartColors: [C.primary, C.green, C.cyan],
    chartArea: { fill: { color: C.white } }, plotArea: { fill: { color: C.white } },
    valAxisMinVal: 0, valAxisMaxVal: 110, valAxisMajorUnit: 20,
    catAxisLabelColor: C.ink, catAxisLabelFontSize: 12, catAxisLabelFontBold: true,
    valAxisLabelColor: C.muted, valAxisLabelFontSize: 11,
    valGridLine: { color: "E2E8F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontBold: true, dataLabelFontSize: 13, dataLabelFormatCode: '0.0"%"',
    showLegend: false, showTitle: false,
  });
  // methodology right
  const x2 = 8.3, w2 = W - M - x2, y = 1.85, h = 4.8;
  card(s, x2, y, w2, h, C.teal);
  s.addText("Phương pháp đánh giá", { x: x2 + 0.3, y: y + 0.25, w: w2 - 0.5, h: 0.4, fontFace: F, fontSize: 17, bold: true, color: C.teal, margin: 0 });
  s.addText([
    { text: "15 golden questions", options: { bold: true, color: C.ink, breakLine: true } },
    { text: "phủ: gợi ý món, FAQ, dị ứng, chính sách, các ca guardrail.", options: { color: C.muted, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Retrieval Hit@5", options: { bold: true, color: C.primary, breakLine: true } },
    { text: "BM25 có lấy đúng nguồn kỳ vọng? → 11/14", options: { color: C.muted, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Guardrail Accuracy", options: { bold: true, color: C.green, breakLine: true } },
    { text: "phát hiện đúng cờ an toàn? → 4/4", options: { color: C.muted, breakLine: true } },
    { text: " ", options: { breakLine: true, fontSize: 6 } },
    { text: "Overall Pass", options: { bold: true, color: C.cyan, breakLine: true } },
    { text: "đạt yêu cầu tổng thể → 12/15", options: { color: C.muted } },
  ], { x: x2 + 0.3, y: y + 0.8, w: w2 - 0.6, h: h - 1.0, fontFace: F, fontSize: 13, paraSpaceAfter: 2, margin: 0 });
  pageNum(s, 9);
})();

// ───────────────────────── Slide 10 — Demo ─────────────────────────
(() => {
  const s = slideBase(true);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.cyan }, line: { type: "none" } });
  s.addShape(p.shapes.OVAL, { x: W - 3.0, y: -1.4, w: 3.6, h: 3.6, fill: { color: C.teal, transparency: 80 }, line: { type: "none" } });
  kicker(s, "Trình diễn", C.cyan);
  s.addText("Demo trực tiếp", { x: M, y: 1.0, w: 11, h: 1.0, fontFace: F, fontSize: 46, bold: true, color: C.white, margin: 0 });
  s.addText("Chạy hệ thống thật: React + .NET + dịch vụ AI. Các kịch bản minh họa:", {
    x: M, y: 2.15, w: 11.5, h: 0.5, fontFace: F, fontSize: 16, color: "CADCFC", margin: 0,
  });
  const demos = [
    [C.primary, "1", "Gợi ý món", "“Gợi ý món cho 2 người ăn trưa” → card món + nút xác nhận."],
    [C.teal, "2", "Hỏi đáp FAQ", "“Mở cửa mấy giờ? Thanh toán thế nào?” → trả lời từ KB."],
    [C.green, "3", "Dị ứng", "“Tôi dị ứng hải sản, tránh món nào?” → tránh đúng món."],
    [C.danger, "4", "Guardrail", "“Hôm nay thời tiết thế nào?” → chặn OUT_OF_SCOPE, kéo về chủ đề."],
  ];
  const w = 5.85, h = 1.7, gx = M, gx2 = M + w + 0.4, gy = 2.95, gy2 = 2.95 + h + 0.3;
  const pos = [[gx, gy], [gx2, gy], [gx, gy2], [gx2, gy2]];
  demos.forEach((d, i) => {
    const [x, y] = pos[i];
    s.addShape(p.shapes.RECTANGLE, { x, y, w, h, fill: { color: "0E3454" }, line: { color: "1C4A70", width: 1 } });
    badge(s, x + 0.28, y + 0.3, d[1], d[0]);
    s.addText(d[2], { x: x + 1.0, y: y + 0.28, w: w - 1.2, h: 0.5, fontFace: F, fontSize: 16, bold: true, color: C.white, valign: "middle", margin: 0 });
    s.addText(d[3], { x: x + 0.3, y: y + 0.92, w: w - 0.6, h: 0.65, fontFace: F, fontSize: 12.8, color: "CADCFC", lineSpacingMultiple: 1.0, margin: 0 });
  });
  pageNum(s, 10);
})();

// ───────────────────────── Slide 11 — Hạn chế & Hướng phát triển ─────────────────────────
(() => {
  const s = slideBase();
  kicker(s, "Đánh giá phản biện");
  title(s, "Hạn chế & Hướng phát triển");
  const y = 1.85, h = 4.9, w = 5.85;
  card(s, M, y, w, h, C.danger);
  s.addText("Hạn chế (Threats to validity)", { x: M + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 17, bold: true, color: C.danger, margin: 0 });
  s.addText([
    { text: "KB nhỏ (35 chunk) → kết quả chưa đại diện quy mô lớn.", options: { bullet: true, breakLine: true } },
    { text: "Golden set 15 câu, do một người gán nhãn → có thiên lệch.", options: { bullet: true, breakLine: true } },
    { text: "Khi không có API, đánh giá chạy ở chế độ RAG-only fallback → chưa phản ánh đầy đủ chất lượng LLM.", options: { bullet: true, breakLine: true } },
    { text: "BM25 dựa từ khóa, chưa hiểu ngữ nghĩa sâu / đồng nghĩa.", options: { bullet: true } },
  ], { x: M + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14, color: C.ink, paraSpaceAfter: 11, margin: 0 });
  const x2 = M + w + 0.4;
  card(s, x2, y, w, h, C.green);
  s.addText("Hướng phát triển", { x: x2 + 0.3, y: y + 0.25, w: w - 0.5, h: 0.45, fontFace: F, fontSize: 17, bold: true, color: C.green, margin: 0 });
  s.addText([
    { text: "Hybrid retrieval: BM25 + embeddings (semantic rerank).", options: { bullet: true, breakLine: true } },
    { text: "Đánh giá faithfulness/hallucination bằng RAGAS.", options: { bullet: true, breakLine: true } },
    { text: "LLM streaming + bộ nhớ hội thoại đa lượt.", options: { bullet: true, breakLine: true } },
    { text: "Tự đồng bộ KB từ database menu của nhà hàng.", options: { bullet: true, breakLine: true } },
    { text: "Mở rộng golden set + nhiều người gán nhãn.", options: { bullet: true } },
  ], { x: x2 + 0.3, y: y + 0.85, w: w - 0.55, h: h - 1.1, fontFace: F, fontSize: 14, color: C.ink, paraSpaceAfter: 11, margin: 0 });
  pageNum(s, 11);
})();

// ───────────────────────── Slide 12 — Kết luận / Cảm ơn ─────────────────────────
(() => {
  const s = slideBase(true);
  s.addShape(p.shapes.RECTANGLE, { x: 0, y: 0, w: 0.22, h: H, fill: { color: C.primary }, line: { type: "none" } });
  s.addShape(p.shapes.OVAL, { x: -1.2, y: H - 2.4, w: 3.6, h: 3.6, fill: { color: C.primary2, transparency: 80 }, line: { type: "none" } });
  s.addShape(p.shapes.OVAL, { x: W - 2.4, y: -1.2, w: 3.2, h: 3.2, fill: { color: C.teal, transparency: 82 }, line: { type: "none" } });
  kicker(s, "Kết luận", C.cyan);
  s.addText("Kết luận", { x: M, y: 1.0, w: 11, h: 0.9, fontFace: F, fontSize: 40, bold: true, color: C.white, margin: 0 });
  s.addText([
    { text: "Chatbot RAG bám sát dữ liệu nhà hàng — trả lời có nguồn, đúng phạm vi.", options: { bullet: true, color: "EAF7FC", breakLine: true } },
    { text: "An toàn nhiều lớp: guardrails + output parser; AI không tự đặt đơn.", options: { bullet: true, color: "EAF7FC", breakLine: true } },
    { text: "Đánh giá định lượng minh bạch và tích hợp vào hệ thống thật.", options: { bullet: true, color: "EAF7FC" } },
  ], { x: M + 0.05, y: 2.2, w: 11.6, h: 2.0, fontFace: F, fontSize: 16.5, paraSpaceAfter: 12, margin: 0 });
  s.addText("Xin cảm ơn thầy cô đã lắng nghe!", { x: M, y: 4.7, w: 11.6, h: 0.7, fontFace: F, fontSize: 26, bold: true, color: C.white, margin: 0 });
  s.addText("Rất mong nhận được câu hỏi & góp ý  ·  Q&A", { x: M, y: 5.5, w: 11.6, h: 0.5, fontFace: F, fontSize: 15, italic: true, color: C.cyan, margin: 0 });
})();

p.writeFile({ fileName: "docs/presentation/CMC_RAG_Chatbot_Defense.pptx" }).then((f) => console.log("WROTE", f));
