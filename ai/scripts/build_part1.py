# -*- coding: utf-8 -*-
"""Build Part I: Data & Preprocessing (no retrieval benchmarks)."""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
nb.metadata.update({
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.0"},
})

def md(src): return nbf.v4.new_markdown_cell(src.strip())
def code(src): return nbf.v4.new_code_cell(src.strip())

cells = []

# === TITLE ===
cells.append(md(
    "# X\u00e2y D\u1ef1ng V\u00e0 \u0110\u00e1nh Gi\u00e1 Chatbot Nh\u00e0 H\u00e0ng D\u1ef1a Tr\u00ean RAG\n\n"
    "**\u0110\u1ed3 \u00e1n:** Restaurant QR AI Ordering  \n"
    "**Ph\u01b0\u01a1ng ph\u00e1p:** Retrieval-Augmented Generation (RAG) v\u1edbi BM25, Dense E5, Hybrid RRF  \n"
    "**Ng\u00f4n ng\u1eef:** Python 3.13 \u00b7 PyTorch \u00b7 Sentence-Transformers\n\n---\n\n"
    "Notebook n\u00e0y tr\u00ecnh b\u00e0y **qu\u00e1 tr\u00ecnh x\u00e2y d\u1ef1ng t\u1eeb \u0111\u1ea7u**, ch\u1ea1y code th\u1eadt t\u1ea1i m\u1ed7i b\u01b0\u1edbc.  \n"
    "M\u1ecdi con s\u1ed1 \u0111\u01b0\u1ee3c t\u00ednh tr\u1ef1c ti\u1ebfp \u2014 kh\u00f4ng d\u00f9ng d\u1eef li\u1ec7u t\u0129nh hay h\u00ecnh \u1ea3nh s\u1eb5n c\u00f3."
))

# === SETUP ===
cells.append(code(
    'import sys, os\n'
    'from pathlib import Path\n'
    'from collections import Counter\n\n'
    'import pandas as pd\n'
    'import matplotlib.pyplot as plt\n'
    'import matplotlib\n'
    'matplotlib.rcParams["figure.dpi"] = 120\n'
    'matplotlib.rcParams["font.size"] = 11\n\n'
    'AI_ROOT = Path(".").resolve()\n'
    'if AI_ROOT.name == "notebooks":\n'
    '    AI_ROOT = AI_ROOT.parent\n'
    'KB_PATH = AI_ROOT / "knowledge-base"\n'
    'PROJECT_ROOT = AI_ROOT.parent\n\n'
    'sys.path.insert(0, str(AI_ROOT))\n'
    'os.chdir(AI_ROOT)\n\n'
    'print(f"AI_ROOT:  {AI_ROOT}")\n'
    'print(f"KB_PATH:  {KB_PATH}")\n'
    'print(f"Python:   {sys.version.split()[0]}")'
))

# === PART I HEADER ===
cells.append(md("---\n# PH\u1ea6N I \u2014 B\u00c0I TO\u00c1N V\u00c0 D\u1eee LI\u1ec6U"))

# === S1 BAI TOAN ===
cells.append(md(
    "## 1. B\u00e0i to\u00e1n\n\n"
    "Kh\u00e1ch h\u00e0ng qu\u00e9t m\u00e3 QR t\u1ea1i b\u00e0n v\u00e0 **chat v\u1edbi AI** \u0111\u1ec3 h\u1ecfi v\u1ec1 menu, gi\u00e1, ch\u00ednh s\u00e1ch,\n"
    "d\u1ecb \u1ee9ng, g\u1ee3i \u00fd m\u00f3n. H\u1ec7 th\u1ed1ng ph\u1ea3i tr\u1ea3 l\u1eddi ch\u00ednh x\u00e1c d\u1ef1a tr\u00ean d\u1eef li\u1ec7u th\u1eadt.\n\n"
    "### 3 r\u00e0ng bu\u1ed9c b\u1ea5t kh\u1ea3 x\u00e2m ph\u1ea1m\n\n"
    "| R\u00e0ng bu\u1ed9c | \u00dd ngh\u0129a | C\u00e1ch \u0111\u1ea3m b\u1ea3o |\n"
    "|---|---|---|\n"
    "| **Grounding** | Kh\u00f4ng b\u1ecba m\u00f3n, kh\u00f4ng b\u1ecba gi\u00e1 | \u0110\u1ed1i chi\u1ebfu menu th\u1eadt tr\u01b0\u1edbc khi tr\u1ea3 l\u1eddi |\n"
    "| **Confirmation** | Kh\u00f4ng t\u1ef1 \u0111\u1eb7t m\u00f3n thay kh\u00e1ch | Guardrail \u2192 frontend hi\u1ec7n n\u00fat x\u00e1c nh\u1eadn |\n"
    "| **Safety** | Kh\u00f4ng ti\u1ebft l\u1ed9 PII / system prompt | Regex + guardrails ch\u1eb7n tr\u01b0\u1edbc LLM |\n\n"
    "### \u0110\u1ea7u ra kh\u00f4ng ch\u1ec9 l\u00e0 v\u0103n b\u1ea3n\n\n"
    "H\u1ec7 th\u1ed1ng tr\u1ea3 v\u1ec1 **structured response** g\u1ed3m: text, decision, evidence IDs,\n"
    "claims, cart actions, session updates \u2014 \u0111\u1ec3 backend ki\u1ec3m tra l\u1ea1i.\n\n"
    "### Ki\u1ebfn tr\u00fac evidence-first\n\n"
    "| Lo\u1ea1i c\u00e2u h\u1ecfi | V\u00ed d\u1ee5 | Ngu\u1ed3n d\u1eef li\u1ec7u | C\u1ea7n LLM? |\n"
    "|---|---|---|---|\n"
    "| Ch\u00e0o h\u1ecfi, c\u1ea3m \u01a1n | \"Xin ch\u00e0o\" | Deterministic | Kh\u00f4ng |\n"
    "| Gi\u00e1 / c\u00f2n b\u00e1n | \"Ph\u1edf b\u00f2 bao nhi\u00eau?\" | Live database (menu API) | C\u00f3 |\n"
    "| FAQ / ch\u00ednh s\u00e1ch | \"Wifi pass l\u00e0 g\u00ec?\" | Knowledge Base \u2192 RAG | C\u00f3 |\n\n"
    "> **Quy\u1ebft \u0111\u1ecbnh:** Evidence-first routing gi\u1ea3m latency, tr\u00e1nh hallucination v\u1ec1 gi\u00e1."
))

# === S2 KNOWLEDGE BASE ===
cells.append(md(
    "## 2. Kh\u00e1m ph\u00e1 Knowledge Base\n\n"
    "Knowledge Base (KB) ch\u1ee9a **tri th\u1ee9c t\u0129nh** c\u1ee7a nh\u00e0 h\u00e0ng: FAQ, ch\u00ednh s\u00e1ch, th\u00f4ng tin\n"
    "d\u1ecb \u1ee9ng, combo, thanh to\u00e1n... d\u01b0\u1edbi d\u1ea1ng file Markdown.\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `knowledge-base/` \u2014 26 file Markdown, load b\u1eb1ng `load_markdown_knowledge_base()`"
))

cells.append(code(
    'from app.rag.knowledge_base import load_markdown_knowledge_base\n\n'
    'kb_chunks = load_markdown_knowledge_base(KB_PATH)\n'
    'print(f"T\u1ed5ng s\u1ed1 chunks: {len(kb_chunks)}")\n'
    'print(f"S\u1ed1 file ngu\u1ed3n:  {len(set(c.source for c in kb_chunks))}")\n'
    'print(f"T\u1ea5t c\u1ea3 c\u00f3 tags: {all(c.tags for c in kb_chunks)}")'
))

cells.append(md("### 2.1 Ph\u00e2n b\u1ed1 chunk theo file ngu\u1ed3n"))

cells.append(code(
    'source_counts = Counter(c.source for c in kb_chunks)\n'
    'source_df = pd.DataFrame([\n'
    '    {"T\u1ec7p ngu\u1ed3n": src, "S\u1ed1 chunk": cnt}\n'
    '    for src, cnt in source_counts.most_common()\n'
    '])\n'
    'display(source_df.style.hide(axis="index"))\n\n'
    'fig, ax = plt.subplots(figsize=(10, 5))\n'
    'ax.barh(source_df["T\u1ec7p ngu\u1ed3n"][::-1], source_df["S\u1ed1 chunk"][::-1], color="#0ea5e9")\n'
    'ax.set_xlabel("S\u1ed1 chunk")\n'
    'ax.set_title("Ph\u00e2n b\u1ed1 chunk theo file ngu\u1ed3n")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md(
    "### 2.2 Ph\u00e2n b\u1ed1 theo m\u1ee9c \u0111\u1ed9 r\u1ee7i ro (risk tier)\n\n"
    "M\u1ed7i chunk \u0111\u01b0\u1ee3c g\u00e1n risk tier d\u1ef1a tr\u00ean **h\u1eadu qu\u1ea3 n\u1ebfu AI tr\u1ea3 l\u1eddi sai**:\n\n"
    "| Risk tier | Ti\u00eau ch\u00ed | V\u00ed d\u1ee5 |\n"
    "|---|---|---|\n"
    "| **critical** | Sai \u2192 nguy h\u1ea1i s\u1ee9c kh\u1ecfe | D\u1ecb \u1ee9ng, cross-contamination |\n"
    "| **high** | Sai \u2192 m\u1ea5t ti\u1ec1n | Ch\u00ednh s\u00e1ch ho\u00e0n ti\u1ec1n, thanh to\u00e1n |\n"
    "| **medium** | Sai \u2192 tr\u1ea3i nghi\u1ec7m k\u00e9m | FAQ, combo g\u1ee3i \u00fd |\n"
    "| **low** | Sai \u2192 kh\u00f4ng \u1ea3nh h\u01b0\u1edfng | L\u1ecbch s\u1eed nh\u00e0 h\u00e0ng, brand voice |"
))

cells.append(code(
    'tier_counts = Counter(c.risk_tier for c in kb_chunks)\n'
    'tier_df = pd.DataFrame([\n'
    '    {"Risk tier": tier, "S\u1ed1 chunk": cnt}\n'
    '    for tier, cnt in sorted(tier_counts.items(), key=lambda x: ["critical","high","medium","low"].index(x[0]))\n'
    '])\n'
    'display(tier_df.style.hide(axis="index"))\n\n'
    'colors = {"critical": "#ef4444", "high": "#f97316", "medium": "#eab308", "low": "#22c55e"}\n'
    'fig, ax = plt.subplots(figsize=(6, 4))\n'
    'ax.bar(tier_df["Risk tier"], tier_df["S\u1ed1 chunk"], color=[colors[t] for t in tier_df["Risk tier"]])\n'
    'ax.set_ylabel("S\u1ed1 chunk")\n'
    'ax.set_title("Ph\u00e2n b\u1ed1 chunk theo risk tier")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

# S2.3 Variants — demo only, no eval
cells.append(md(
    "### 2.3 Question variants \u2014 l\u00e0m gi\u00e0u index cho BM25\n\n"
    "BM25 ch\u1ec9 match **t\u1eeb ch\u00ednh x\u00e1c**. N\u1ebfu heading l\u00e0 *\"Ti\u1ec7n Nghi\"* m\u00e0 kh\u00e1ch h\u1ecfi\n"
    "*\"wifi pass\"* \u2192 kh\u00f4ng c\u00f3 t\u1eeb chung \u2192 miss.\n\n"
    "**Gi\u1ea3i ph\u00e1p:** Th\u00eam `<!-- question_variants: wifi, pass wifi -->`\n"
    "ngay sau heading. Khi chunking, variants \u0111\u01b0\u1ee3c n\u1ed1i v\u00e0o content \u2192 BM25 c\u00f3 th\u00eam t\u1eeb kh\u00f3a."
))

cells.append(code(
    'import re\n\n'
    'variant_files = []\n'
    'no_variant_files = []\n'
    'for f in sorted(KB_PATH.glob("*.md")):\n'
    '    text = f.read_text(encoding="utf-8")\n'
    '    count = len(re.findall(r"question_variants", text))\n'
    '    if count > 0:\n'
    '        variant_files.append({"T\u1ec7p": f.name, "S\u1ed1 variant line": count})\n'
    '    else:\n'
    '        no_variant_files.append(f.name)\n\n'
    'print(f"Files C\u00d3 question variants:  {len(variant_files)}/26")\n'
    'print(f"Files KH\u00d4NG c\u1ea7n variants:    {len(no_variant_files)}/26")\n'
    'print()\n'
    'display(pd.DataFrame(variant_files).style.hide(axis="index").set_caption("Files C\u00d3 question variants"))'
))

cells.append(md(
    "#### Minh h\u1ecda c\u01a1 ch\u1ebf: Variants gi\u00fap BM25 v\u01b0\u1ee3t vocabulary mismatch\n\n"
    "3 queries m\u00e0 kh\u00e1ch d\u00f9ng t\u1eeb kh\u00e1c heading KB:"
))

cells.append(code(
    'from app.rag.retriever import BM25Retriever\n'
    'from app.rag.knowledge_base import KnowledgeChunk\n'
    'import re as _re\n\n'
    'bm25_with = BM25Retriever(kb_chunks)\n\n'
    'stripped_chunks = [KnowledgeChunk(\n'
    '    source=c.source, title=c.title,\n'
    '    content=_re.sub(r"question_variants:.*", "", c.content),\n'
    '    tags=c.tags, chunk_id=c.chunk_id, risk_tier=c.risk_tier,\n'
    ') for c in kb_chunks]\n'
    'bm25_without = BM25Retriever(stripped_chunks)\n\n'
    'demo_queries = [\n'
    '    ("c\u00f3 ch\u1ed7 \u0111\u1eadu xe kh\u00f4ng?",  "restaurant-info.md",    "Heading \'G\u1eedi Xe\' \u2014 kh\u00e1ch n\u00f3i \'\u0111\u1eadu xe\'"),\n'
    '    ("m\u00f3n n\u00e0o kh\u00f4ng cay?",     "spice-flavor-scale.md", "Heading \'Thang Cay\' \u2014 kh\u00e1ch n\u00f3i \'kh\u00f4ng cay\'"),\n'
    '    ("m\u1ee9c cay m\u1ea5y?",           "spice-flavor-scale.md", "Heading \'Thang Cay\' \u2014 kh\u00e1ch n\u00f3i \'m\u1ee9c cay\'"),\n'
    ']\n\n'
    'rows = []\n'
    'for query, expected, explanation in demo_queries:\n'
    '    rw = bm25_with.search(query, top_k=1)\n'
    '    rwo = bm25_without.search(query, top_k=1)\n'
    '    hit_w = rw[0].chunk.source if rw else "(miss)"\n'
    '    hit_wo = rwo[0].chunk.source if rwo else "(miss)"\n'
    '    ok_w = "\u2713" if rw and expected in hit_w else "\u2717"\n'
    '    ok_wo = "\u2713" if rwo and expected in hit_wo else "\u2717"\n'
    '    rows.append({"Query": query, "Vocabulary mismatch": explanation,\n'
    '        "C\u00d3 variants": f"{ok_w} {hit_w}", "KH\u00d4NG variants": f"{ok_wo} {hit_wo}"})\n'
    'display(pd.DataFrame(rows).style.hide(axis="index").set_caption(\n'
    '    "Minh h\u1ecda: variants gi\u00fap BM25 v\u01b0\u1ee3t vocabulary mismatch"))'
))

cells.append(md(
    "Variants l\u00e0 k\u1ef9 thu\u1eadt **document expansion** \u2014 th\u00eam t\u1eeb kh\u00f3a v\u00e0o document \u0111\u1ec3 BM25\n"
    "c\u00f3 th\u1ec3 match. Impact s\u1ebd \u0111\u01b0\u1ee3c \u0111o l\u01b0\u1eddng ch\u00ednh th\u1ee9c trong Ph\u1ea7n II."
))

# S2.4 Chunking
cells.append(md(
    "### 2.4 Chi\u1ebfn l\u01b0\u1ee3c chunking\n\n"
    "M\u1ed7i file Markdown \u0111\u01b0\u1ee3c chia th\u00e0nh chunks theo **heading c\u1ea5p 2 (`##`)**.\n\n"
    "| Chi\u1ebfn l\u01b0\u1ee3c | \u01afu \u0111i\u1ec3m | Nh\u01b0\u1ee3c \u0111i\u1ec3m |\n"
    "|---|---|---|\n"
    "| Theo paragraph | Chunk nh\u1ecf, c\u1ee5 th\u1ec3 | Qu\u00e1 ng\u1eafn \u2192 thi\u1ebfu ng\u1eef c\u1ea3nh |\n"
    "| Theo file | \u0110\u1ea7y \u0111\u1ee7 ng\u1eef c\u1ea3nh | Qu\u00e1 d\u00e0i \u2192 retrieval k\u00e9m |\n"
    "| **Theo heading c\u1ea5p 2** | C\u00e2n b\u1eb1ng | Chunk size kh\u00f4ng \u0111\u1ec1u |"
))

cells.append(code(
    'import numpy as np\n\n'
    'word_counts = [len(c.content.split()) for c in kb_chunks]\n'
    'char_counts = [len(c.content) for c in kb_chunks]\n\n'
    'stats = pd.DataFrame([{\n'
    '    "Metric": "S\u1ed1 t\u1eeb / chunk",\n'
    '    "Min": min(word_counts), "Max": max(word_counts),\n'
    '    "Trung b\u00ecnh": f"{np.mean(word_counts):.0f}",\n'
    '    "Trung v\u1ecb": f"{np.median(word_counts):.0f}",\n'
    '}, {\n'
    '    "Metric": "S\u1ed1 k\u00fd t\u1ef1 / chunk",\n'
    '    "Min": min(char_counts), "Max": max(char_counts),\n'
    '    "Trung b\u00ecnh": f"{np.mean(char_counts):.0f}",\n'
    '    "Trung v\u1ecb": f"{np.median(char_counts):.0f}",\n'
    '}])\n'
    'display(stats.style.hide(axis="index").set_caption("Th\u1ed1ng k\u00ea k\u00edch th\u01b0\u1edbc chunk"))\n\n'
    'fig, ax = plt.subplots(figsize=(8, 4))\n'
    'ax.hist(word_counts, bins=20, color="#06b6d4", edgecolor="white")\n'
    'ax.axvline(np.median(word_counts), color="#ef4444", linestyle="--", label=f"Median = {np.median(word_counts):.0f}")\n'
    'ax.set_xlabel("S\u1ed1 t\u1eeb")\n'
    'ax.set_ylabel("S\u1ed1 chunk")\n'
    'ax.set_title(f"Ph\u00e2n b\u1ed1 k\u00edch th\u01b0\u1edbc {len(kb_chunks)} chunks")\n'
    'ax.legend()\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md("### 2.5 V\u00ed d\u1ee5 chunk th\u1eadt"))

cells.append(code(
    'samples = {}\n'
    'for c in kb_chunks:\n'
    '    if c.risk_tier not in samples:\n'
    '        samples[c.risk_tier] = c\n'
    '    if len(samples) >= 3:\n'
    '        break\n\n'
    'for tier, chunk in samples.items():\n'
    '    words = len(chunk.content.split())\n'
    '    print(f"{\'=\'*60}")\n'
    '    print(f"Risk tier : {tier}")\n'
    '    print(f"Source    : {chunk.source}")\n'
    '    print(f"Title     : {chunk.title}")\n'
    '    print(f"K\u00edch th\u01b0\u1edbc: {words} t\u1eeb, {len(chunk.content)} k\u00fd t\u1ef1")\n'
    '    print(f"Tags      : {\', \'.join(chunk.tags[:5])}")\n'
    '    print(f"Content   : {chunk.content[:200]}...")\n'
    '    print()'
))

# === S3 NORMALIZE — demo only ===
cells.append(md(
    "## 3. Chu\u1ea9n h\u00f3a ti\u1ebfng Vi\u1ec7t\n\n"
    "Ti\u1ebfng Vi\u1ec7t t\u1ef1 nhi\u00ean c\u00f3 nhi\u1ec1u bi\u1ebfn th\u1ec3 c\u1ea7n chu\u1ea9n h\u00f3a **tr\u01b0\u1edbc khi** truy xu\u1ea5t:\n"
    "- **Vi\u1ebft t\u1eaft**: \"ko\" \u2192 \"kh\u00f4ng\", \"dc\" \u2192 \"\u0111\u01b0\u1ee3c\", \"bn\" \u2192 \"bao nhi\u00eau\"\n"
    "- **Kh\u00f4ng d\u1ea5u**: \"hai san\" \u2192 \"h\u1ea3i s\u1ea3n\"\n"
    "- **Emoji**: \U0001f336\ufe0f \u2192 \"cay\", \U0001f990 \u2192 \"t\u00f4m\"\n"
    "- **Gen-Z**: \"h\u00f4ng\" \u2192 \"kh\u00f4ng\", \"ntn\" \u2192 \"nh\u01b0 th\u1ebf n\u00e0o\""
))

cells.append(md("### 3.1 Demo chu\u1ea9n h\u00f3a \u2014 b\u1ea3ng before / after"))

cells.append(code(
    'from app.rag.vietnamese_normalizer import normalize_query_text, normalize_vietnamese\n\n'
    'test_cases = [\n'
    '    "ko co mon nao ngon ko?",\n'
    '    "hai san tuoi khong?",\n'
    '    "budget 500k cho 3 nguoi",\n'
    '    "dc ko, bn tien?",\n'
    '    "PHAI KHONG????",\n'
    '    "pho bo bao nhieu tien",\n'
    ']\n\n'
    'norm_rows = []\n'
    'for q in test_cases:\n'
    '    norm_rows.append({\n'
    '        "C\u00e2u g\u1ed1c": q,\n'
    '        "normalize_query_text()": normalize_query_text(q),\n'
    '        "normalize_vietnamese()": normalize_vietnamese(q),\n'
    '    })\n\n'
    'display(pd.DataFrame(norm_rows).style.hide(axis="index"))'
))

cells.append(md(
    "### 3.2 Hai h\u00e0m normalize \u2014 m\u1ee5c \u0111\u00edch kh\u00e1c nhau\n\n"
    "| H\u00e0m | M\u1ee5c \u0111\u00edch | D\u00f9ng \u1edf \u0111\u00e2u |\n"
    "|---|---|---|\n"
    "| `normalize_query_text()` | **BM25 matching** \u2014 strip d\u1ea5u, teencode, emoji | Built-in BM25 tokenizer |\n"
    "| `normalize_vietnamese()` | **NLU** \u2014 gi\u1eef d\u1ea5u, ch\u1ec9 s\u1eeda teencode | Intent detection, LLM prompt |\n\n"
    "`normalize_query_text()` \u0111\u01b0\u1ee3c g\u1ecdi **b\u00ean trong** BM25 tokenizer \u2014\n"
    "c\u1ea3 l\u00fac index documents l\u1eabn l\u00fac search. Impact c\u1ee7a normalize s\u1ebd \u0111\u01b0\u1ee3c\n"
    "\u0111o l\u01b0\u1eddng ch\u00ednh th\u1ee9c trong Ph\u1ea7n II."
))

# === S4 EVAL SET ===
cells.append(md(
    "## 4. T\u1eadp \u0111\u00e1nh gi\u00e1 retrieval\n\n"
    "\u0110\u1ec3 so s\u00e1nh c\u00e1c ph\u01b0\u01a1ng ph\u00e1p retrieval **c\u00f4ng b\u1eb1ng**, c\u1ea7n t\u1eadp d\u1eef li\u1ec7u\n"
    "v\u1edbi nh\u00e3n ch\u00ednh x\u00e1c.\n\n"
    "### Ph\u01b0\u01a1ng ph\u00e1p x\u00e2y d\u1ef1ng\n\n"
    "1. **Family-based design**: M\u1ed7i intent c\u00f3 1 template, sinh 5 query variants.\n"
    "2. **Curated templates**: Vi\u1ebft tay, d\u1ef1a tr\u00ean log chat th\u1eadt.\n"
    "3. **Engineering review**: G\u00e1n `expected_selectors` v\u00e0 `forbidden_selectors`.\n"
    "4. **Frozen test split**: `dev` (th\u1eed nghi\u1ec7m) v\u00e0 `test` (b\u1ecb kh\u00f3a, ch\u1ec9 d\u00f9ng cu\u1ed1i).\n"
    "5. **Augmented cases**: 53 noisy + 19 vocab-mismatch \u0111\u1ec3 test preprocessing."
))

cells.append(code(
    'import json\n\n'
    'eval_path = AI_ROOT / "evaluation" / "datasets" / "retrieval_cases.dev.v1.jsonl"\n'
    'eval_cases = [json.loads(line) for line in open(eval_path, "r", encoding="utf-8")]\n\n'
    'original = [c for c in eval_cases if not c.get("noise_type")]\n'
    'noisy = [c for c in eval_cases if c.get("noise_type") in ("no-diacritics", "teencode+no-diac")]\n'
    'vocab = [c for c in eval_cases if c.get("noise_type") == "vocab-mismatch"]\n\n'
    'print(f"T\u1ed5ng s\u1ed1 cases:     {len(eval_cases)}")\n'
    'print(f"  Original:        {len(original)}")\n'
    'print(f"  Noisy augmented: {len(noisy)}")\n'
    'print(f"  Vocab mismatch:  {len(vocab)}")\n'
    'print(f"Positive cases:    {sum(1 for c in eval_cases if c.get(\'expected_selectors\'))}")\n'
    'print(f"Negative cases:    {sum(1 for c in eval_cases if not c.get(\'expected_selectors\'))}")'
))

cells.append(md("### 4.1 Ph\u00e2n b\u1ed1 theo intent"))

cells.append(code(
    'intent_counts = Counter(c["intent"] for c in eval_cases)\n'
    'intent_df = pd.DataFrame([\n'
    '    {"Intent": intent, "S\u1ed1 case": count, "T\u1ef7 l\u1ec7": f"{count/len(eval_cases):.0%}"}\n'
    '    for intent, count in intent_counts.most_common()\n'
    '])\n'
    'display(intent_df.style.hide(axis="index"))\n\n'
    'fig, ax = plt.subplots(figsize=(8, 4))\n'
    'ax.barh(intent_df["Intent"][::-1], intent_df["S\u1ed1 case"][::-1], color="#8b5cf6")\n'
    'ax.set_xlabel("S\u1ed1 case")\n'
    'ax.set_title(f"Ph\u00e2n b\u1ed1 {len(eval_cases)} eval cases theo intent")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md("### 4.2 V\u00ed d\u1ee5 eval case"))

cells.append(code(
    'seen_intents = set()\n'
    'example_rows = []\n'
    'for c in eval_cases:\n'
    '    if c["intent"] not in seen_intents and len(example_rows) < 5:\n'
    '        seen_intents.add(c["intent"])\n'
    '        example_rows.append({\n'
    '            "Case ID": c["case_id"],\n'
    '            "Intent": c["intent"],\n'
    '            "Query": c["query"][:50],\n'
    '            "Expected": str(c.get("expected_selectors", []))[:40],\n'
    '        })\n'
    'display(pd.DataFrame(example_rows).style.hide(axis="index"))'
))

cells.append(md(
    "### 4.3 Negative cases \u2014 out_of_catalog\n\n"
    "15 cases h\u1ecfi v\u1ec1 th\u1ee9 nh\u00e0 h\u00e0ng **kh\u00f4ng c\u00f3** (gluten-free, keto, halal).\n"
    "Retrieval **kh\u00f4ng n\u00ean** t\u00ecm th\u1ea5y document ph\u00f9 h\u1ee3p."
))

cells.append(code(
    'negative_cases = [c for c in eval_cases if not c.get("expected_selectors")]\n'
    'neg_df = pd.DataFrame([{\n'
    '    "Case ID": c["case_id"],\n'
    '    "Query": c["query"][:50],\n'
    '    "Guardrail": ", ".join(c.get("guardrail_flags", [])),\n'
    '} for c in negative_cases[:6]])\n'
    'display(neg_df.style.hide(axis="index"))\n'
    'print(f"T\u1ed5ng negative cases: {len(negative_cases)}")'
))

# === CONCLUSION ===
cells.append(md(
    "---\n"
    "## K\u1ebft lu\u1eadn Ph\u1ea7n I\n\n"
    "### L\u01b0u \u00fd v\u1ec1 d\u1eef li\u1ec7u\n\n"
    "\u0110\u00e2y l\u00e0 d\u1ef1 \u00e1n t\u1ef1 x\u00e2y d\u1ef1ng \u2014 KB, eval set, v\u00e0 c\u00e1c ph\u01b0\u01a1ng ph\u00e1p \u0111\u1ec1u do nh\u00f3m ph\u00e1t tri\u1ec3n.\n"
    "K\u1ebft qu\u1ea3 ch\u1ec9 ph\u1ea3n \u00e1nh hi\u1ec7u qu\u1ea3 tr\u00ean **b\u1ed9 d\u1eef li\u1ec7u c\u1ee5 th\u1ec3 n\u00e0y** (26 files KB, 197 eval cases),\n"
    "kh\u00f4ng generalize ra c\u00e1c domain kh\u00e1c.\n\n"
    "### \u0110\u00e3 chu\u1ea9n b\u1ecb\n\n"
    "| Th\u00e0nh ph\u1ea7n | Chi ti\u1ebft |\n"
    "|---|---|\n"
    "| **Knowledge Base** | 26 files Markdown \u2192 213 chunks, 4 risk tiers |\n"
    "| **Preprocessing** | Normalize (teencode + kh\u00f4ng d\u1ea5u + emoji), Question variants (14/26 files) |\n"
    "| **Eval set** | 197 cases: 125 original + 53 noisy + 19 vocab-mismatch + 15 negative |\n\n"
    "### C\u00e2u h\u1ecfi Ph\u1ea7n II s\u1ebd tr\u1ea3 l\u1eddi\n\n"
    "V\u1edbi d\u1eef li\u1ec7u \u0111\u00e3 chu\u1ea9n b\u1ecb, Ph\u1ea7n II s\u1ebd x\u00e2y d\u1ef1ng v\u00e0 so s\u00e1nh **3 ph\u01b0\u01a1ng ph\u00e1p retrieval**:\n\n"
    "1. **BM25** (lexical) \u2014 match t\u1eeb ch\u00ednh x\u00e1c, c\u00f3 normalize built-in\n"
    "2. **Dense E5** (semantic) \u2014 encode th\u00e0nh vector, so s\u00e1nh theo ngh\u0129a\n"
    "3. **Hybrid RRF** \u2014 k\u1ebft h\u1ee3p BM25 + Dense b\u1eb1ng Reciprocal Rank Fusion\n\n"
    "> Ph\u01b0\u01a1ng ph\u00e1p n\u00e0o t\u1ed1t nh\u1ea5t tr\u00ean b\u1ed9 d\u1eef li\u1ec7u t\u1ef1 x\u00e2y c\u1ee7a ch\u00fang t\u00f4i?\n"
    "> Normalize v\u00e0 variants th\u1ef1c s\u1ef1 c\u1ea3i thi\u1ec7n bao nhi\u00eau?\n"
    "> V\u00e0 c\u00e1i gi\u00e1 ph\u1ea3i tr\u1ea3 (latency, complexity) c\u00f3 x\u1ee9ng \u0111\u00e1ng kh\u00f4ng?"
))

# === WRITE ===
nb.cells = cells
out_path = Path(r"d:\01_Projects\Fable\restaurant-qr-ai-ordering\ai\notebooks\rag_retrieval_research.ipynb")
nbf.write(nb, str(out_path))
print(f"Wrote {out_path} ({len(cells)} cells)")
