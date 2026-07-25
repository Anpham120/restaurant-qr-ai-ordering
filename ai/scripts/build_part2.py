# -*- coding: utf-8 -*-
"""Build Part II: Retrieval Methods Comparison — full version with all improvements."""
import nbformat as nbf
from pathlib import Path

_AI_ROOT = Path(__file__).resolve().parent.parent
nb_path = _AI_ROOT / "notebooks" / "rag_retrieval_research.ipynb"

HIT5_SCREENING_VS_RELEASE_MD = (
    "### Hit@5: screening notebook vs release gate\n\n"
    "| Bộ | N | Artifact | Mục đích |\n"
    "|---|---:|---|---|\n"
    "| **Screening notebook** | 107 | `notebook_retrieval_screening.json` | So sánh BM25 / Dense / Hybrid trong Part II (execute Part II) |\n"
    "| **Release dev gate** | 110 | `dev_retrieval_summary.v3.json` | Gate staging (`AI_STAGING_READINESS.md`); khác bộ case và có thể khác cấu hình E5 |\n\n"
    "> Hai con số **không** so sánh trực tiếp — cột Hybrid trong §15 là **screening**, không phải release 99%."
)
nb = nbf.read(str(nb_path), as_version=4)

def md(src): return nbf.v4.new_markdown_cell(src.strip())
def code(src): return nbf.v4.new_code_cell(src.strip())

cells = nb.cells

# ===== PART II HEADER =====
cells.append(md("# PH\u1ea6N II \u2014 SO S\u00c1NH C\u00c1C PH\u01af\u01a0NG PH\u00c1P RETRIEVAL"))

# ===== S5 OVERVIEW =====
cells.append(md(
    "## 5. Ba ph\u01b0\u01a1ng ph\u00e1p retrieval\n\n"
    "| Ph\u01b0\u01a1ng ph\u00e1p | Lo\u1ea1i | C\u01a1 ch\u1ebf | \u01afu \u0111i\u1ec3m | Nh\u01b0\u1ee3c \u0111i\u1ec3m |\n"
    "|---|---|---|---|---|\n"
    "| **BM25** | Lexical | Kh\u1edbp t\u1eeb ch\u00ednh x\u00e1c (TF-IDF) | Nhanh, kh\u00f4ng c\u1ea7n GPU | Kh\u00f4ng hi\u1ec3u ngh\u0129a |\n"
    "| **Dense E5** | Semantic | Cosine similarity tr\u00ean embedding | Hi\u1ec3u paraphrase, \u0111a ng\u00f4n ng\u1eef | C\u1ea7n load model |\n"
    "| **Hybrid RRF** | K\u1ebft h\u1ee3p | Reciprocal Rank Fusion | B\u00f9 nh\u01b0\u1ee3c \u0111i\u1ec3m cho nhau | Ph\u1ee9c t\u1ea1p nh\u1ea5t |"
))

# S5.1 BM25
cells.append(md(
    "### 5.1 BM25 (Lexical)\n\n"
    "Okapi BM25: TF-IDF + document length normalization.\n"
    "Tokenizer c\u00f3 `normalize_query_text()` built-in + question variants n\u1ed1i v\u00e0o chunk."
))
cells.append(code(
    'import time\n'
    'from app.rag.retriever import BM25Retriever\n\n'
    't0 = time.perf_counter()\n'
    'bm25 = BM25Retriever(kb_chunks)\n'
    'print(f"BM25 index: {(time.perf_counter()-t0)*1000:.0f}ms, {len(kb_chunks)} chunks")\n'
    'for r in bm25.search("nh\u00e0 h\u00e0ng c\u00f3 wifi kh\u00f4ng?", top_k=3):\n'
    '    print(f"  {r.score:.2f}  {r.chunk.source}  [{r.chunk.title}]")'
))

# S5.2 Dense
cells.append(md(
    "### 5.2 Dense E5 (Semantic)\n\n"
    "Trong notebook và báo cáo, **Dense E5** là tên phương pháp; trên hệ thống cùng một encoder "
    "được cấu hình bằng alias **`e5_small`** (model HuggingFace "
    "`intfloat/multilingual-e5-small`, 120MB, 384d).\n"
    "Prefix: `\"query: \"` / `\"passage: \"`. Cosine similarity = dot product (normalized)."
))
cells.append(code(
    'from app.rag.embedding_retriever import DenseRetriever, create_encoder\n\n'
    't0 = time.perf_counter()\n'
    'encoder = create_encoder("e5_small")\n'
    'print(f"Encoder load: {(time.perf_counter()-t0)*1000:.0f}ms")\n\n'
    't0 = time.perf_counter()\n'
    'dense = DenseRetriever(kb_chunks, encoder)\n'
    'print(f"Doc encoding: {(time.perf_counter()-t0)*1000:.0f}ms")\n'
    'print(f"Model: {encoder.model_name}, dim={encoder.dimension}")\n\n'
    'for r in dense.search("nh\u00e0 h\u00e0ng c\u00f3 wifi kh\u00f4ng?", top_k=3):\n'
    '    print(f"  {r.score:.4f}  {r.chunk.source}  [{r.chunk.title}]")'
))

# S5.3 Hybrid
cells.append(md(
    "### 5.3 Hybrid RRF\n\n"
    "$$RRF(d) = \\sum_{r} \\frac{w_r}{k + rank_r(d)}$$\n\n"
    "`k=60`, `w=1.0` cho c\u1ea3 BM25 v\u00e0 Dense."
))
cells.append(code(
    'from app.rag.hybrid_retriever import HybridRrfRetriever\n\n'
    'hybrid = HybridRrfRetriever([bm25, dense])\n'
    'print("Hybrid RRF: BM25 + Dense E5")\n'
    'for r in hybrid.search("nh\u00e0 h\u00e0ng c\u00f3 wifi kh\u00f4ng?", top_k=3):\n'
    '    print(f"  {r.score:.6f}  {r.chunk.source}  [{r.chunk.title}]")'
))

# ===== S6 BENCHMARK =====
cells.append(md(
    "## 6. \u0110\u00e1nh gi\u00e1 tr\u00ean eval set\n\n"
    "### Scope v\u00e0 Metric\n\n"
    "- **107 KB-relevant cases** (35 clean + 53 noisy + 19 vocab-mismatch)\n"
    "- Kh\u00f4ng t\u00ednh menu cases (category/tag) v\u00ec KB retriever kh\u00f4ng x\u1eed l\u00fd\n"
    "- **Hit@1**: document \u0111\u00fang l\u00e0 k\u1ebft qu\u1ea3 \u0111\u1ea7u ti\u00ean? (\u01b0u ti\u00ean production)\n"
    "- **Hit@5**: document \u0111\u00fang n\u1eb1m trong top-5?\n\n"
    "> **L\u01b0u \u00fd th\u1ed1ng k\u00ea:** V\u1edbi n=19 (vocab mismatch), sai 1 case = thay \u0111\u1ed5i ~5%.\n"
    "> C\u00e1c kh\u00e1c bi\u1ec7t nh\u1ecf tr\u00ean t\u1eadp n\u00e0y c\u00f3 th\u1ec3 do ng\u1eabu nhi\u00ean, kh\u00f4ng n\u00ean k\u1ebft lu\u1eadn qu\u00e1 m\u1ea1nh.\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `evaluation/datasets/retrieval_cases.dev.v1.jsonl` (107 KB cases)\n"
    "> Retriever: `BM25Retriever` + `DenseE5Retriever` + `HybridRrfRetriever` t\u1eeb Part I KB"
))

cells.append(code(
    'import json\n\n'
    'eval_cases = [json.loads(l) for l in open(\n'
    '    AI_ROOT / "evaluation" / "datasets" / "retrieval_cases.dev.v1.jsonl",\n'
    '    "r", encoding="utf-8"\n'
    ')]\n\n'
    'clean_kb = [c for c in eval_cases if c.get("expected_selectors")\n'
    '    and any(s.startswith("kb-source") for s in c["expected_selectors"])\n'
    '    and not c.get("noise_type")]\n'
    'noisy = [c for c in eval_cases if c.get("noise_type") in ("no-diacritics", "teencode+no-diac")]\n'
    'vocab = [c for c in eval_cases if c.get("noise_type") == "vocab-mismatch"]\n'
    'negative = [c for c in eval_cases if not c.get("expected_selectors")]\n'
    'kb_cases = clean_kb + noisy + vocab\n\n'
    'print(f"KB cases: {len(kb_cases)} (clean={len(clean_kb)}, noisy={len(noisy)}, vocab={len(vocab)})")\n'
    'print(f"Negative: {len(negative)}")'
))

# S6.1 Main comparison
cells.append(md("### 6.1 K\u1ebft qu\u1ea3 t\u1ed5ng h\u1ee3p (Hit@1 v\u00e0 Hit@5)"))

cells.append(code(
    'def eval_hits(retriever, cases, top_k=5):\n'
    '    hit1 = hit5 = 0\n'
    '    for c in cases:\n'
    '        if not c.get("expected_selectors"): continue\n'
    '        results = retriever.search(c["query"], top_k=top_k)\n'
    '        sources = [r.chunk.source for r in results]\n'
    '        matched = lambda srcs: any(\n'
    '            any(sel.split(":")[-1] in s for s in srcs)\n'
    '            for sel in c["expected_selectors"]\n'
    '        )\n'
    '        if matched(sources[:1]): hit1 += 1\n'
    '        if matched(sources[:5]): hit5 += 1\n'
    '    return hit1, hit5\n\n'
    'methods = {"BM25": bm25, "Dense E5": dense, "Hybrid RRF": hybrid}\n'
    'groups = [("Clean KB", clean_kb), ("Noisy", noisy), ("Vocab mismatch", vocab), ("T\u1ed5ng KB", kb_cases)]\n\n'
    'rows = []\n'
    'chart_data = {}\n'
    'for gname, gcases in groups:\n'
    '    n = len(gcases)\n'
    '    row = {"T\u1eadp": f"{gname} ({n})"}\n'
    '    for mname, ret in methods.items():\n'
    '        h1, h5 = eval_hits(ret, gcases)\n'
    '        row[f"{mname} @1"] = f"{h1}/{n} ({h1/n:.0%})"\n'
    '        row[f"{mname} @5"] = f"{h5}/{n} ({h5/n:.0%})"\n'
    '        chart_data[(gname, mname)] = h5 / n\n'
    '    rows.append(row)\n\n'
    'display(pd.DataFrame(rows).style.hide(axis="index").set_caption(\n'
    '    "Hit@1 v\u00e0 Hit@5: 3 ph\u01b0\u01a1ng ph\u00e1p retrieval"))'
))

# Bar chart
cells.append(code(
    'import numpy as np\n\n'
    'gnames = ["Clean KB", "Noisy", "Vocab mismatch", "T\u1ed5ng KB"]\n'
    'mnames = ["BM25", "Dense E5", "Hybrid RRF"]\n'
    'colors = {"BM25": "#3b82f6", "Dense E5": "#8b5cf6", "Hybrid RRF": "#10b981"}\n\n'
    'x = np.arange(len(gnames))\n'
    'width = 0.25\n\n'
    'fig, ax = plt.subplots(figsize=(10, 5))\n'
    'for i, m in enumerate(mnames):\n'
    '    vals = [chart_data[(g, m)] for g in gnames]\n'
    '    bars = ax.bar(x + i*width, vals, width, label=m, color=colors[m])\n'
    '    for bar, val in zip(bars, vals):\n'
    '        ax.text(bar.get_x()+bar.get_width()/2., bar.get_height()+0.01,\n'
    '                f"{val:.0%}", ha="center", va="bottom", fontsize=9)\n\n'
    'ax.set_ylabel("Hit@5")\n'
    'ax.set_title("So s\u00e1nh 3 ph\u01b0\u01a1ng ph\u00e1p retrieval (b\u1ed9 d\u1eef li\u1ec7u t\u1ef1 x\u00e2y)")\n'
    'ax.set_xticks(x + width)\n'
    'ax.set_xticklabels(gnames)\n'
    'ax.set_ylim(0, 1.15)\n'
    'ax.legend()\n'
    'ax.axhline(y=1.0, color="#e5e7eb", linestyle="--", linewidth=0.8)\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

# S6.2 Negative cases
cells.append(md(
    "### 6.2 False Positive \u2014 Negative cases\n\n"
    "15 cases h\u1ecfi v\u1ec1 th\u1ee9 nh\u00e0 h\u00e0ng **kh\u00f4ng c\u00f3** (gluten-free, keto, halal).\n"
    "Retriever **kh\u00f4ng n\u00ean** tr\u1ea3 v\u1ec1 document n\u00e0o c\u00f3 score cao.\n\n"
    "False positive nguy hi\u1ec3m v\u00ec AI s\u1ebd d\u1ef1a v\u00e0o document sai \u0111\u1ec3 tr\u1ea3 l\u1eddi \u2014\n"
    "kh\u00e1ch h\u00e0ng ngh\u0129 nh\u00e0 h\u00e0ng c\u00f3 m\u00f3n \u0111\u00f3."
))

cells.append(code(
    '# For negatives: check if retriever returns HIGH confidence results\n'
    'fp_rows = []\n'
    'for mname, ret in methods.items():\n'
    '    fp_count = 0\n'
    '    for c in negative:\n'
    '        results = ret.search(c["query"], top_k=5)\n'
    '        if results and results[0].score > 0:\n'
    '            fp_count += 1\n'
    '    fp_rows.append({\n'
    '        "Ph\u01b0\u01a1ng ph\u00e1p": mname,\n'
    '        "Tr\u1ea3 v\u1ec1 k\u1ebft qu\u1ea3": f"{fp_count}/{len(negative)}",\n'
    '        "T\u1ef7 l\u1ec7 false positive": f"{fp_count/len(negative):.0%}",\n'
    '    })\n'
    'display(pd.DataFrame(fp_rows).style.hide(axis="index").set_caption(\n'
    '    "False positive tr\u00ean negative cases"))\n\n'
    '# Show example false positive\n'
    'print("\\nV\u00ed d\u1ee5 negative case v\u00e0 k\u1ebft qu\u1ea3 retrieval:")\n'
    'for c in negative[:3]:\n'
    '    print(f"\\n  Query: {c[\'query\']}")\n'
    '    for mname, ret in methods.items():\n'
    '        results = ret.search(c["query"], top_k=1)\n'
    '        if results:\n'
    '            print(f"    {mname:12s}: {results[0].score:.4f}  {results[0].chunk.source} [{results[0].chunk.title}]")\n'
    '        else:\n'
    '            print(f"    {mname:12s}: (no results)")'
))

cells.append(md(
    "#### Nh\u1eadn x\u00e9t False Positive\n\n"
    "T\u1ea5t c\u1ea3 retriever \u0111\u1ec1u tr\u1ea3 v\u1ec1 k\u1ebft qu\u1ea3 cho negative cases \u2014 \u0111\u00e2y l\u00e0 h\u1ea1n ch\u1ebf\n"
    "c\u1ee7a retrieval n\u00f3i chung: ch\u00fang lu\u00f4n tr\u1ea3 v\u1ec1 g\u1ea7n nh\u1ea5t, kh\u00f4ng bi\u1ebft n\u00f3i \"kh\u00f4ng c\u00f3\".\n\n"
    "**Gi\u1ea3i ph\u00e1p trong production:** Guardrail flags + LLM \u0111\u1ec3 ph\u00e1n \u0111o\u00e1n\n"
    "\"document n\u00e0y c\u00f3 th\u1ef1c s\u1ef1 tr\u1ea3 l\u1eddi c\u00e2u h\u1ecfi kh\u00f4ng?\" tr\u01b0\u1edbc khi respond."
))

# S6.3 Case analysis
cells.append(md(
    "### 6.3 Ph\u00e2n t\u00edch case \u2014 ai c\u1ee9u ai?\n\n"
    "Tr\u00ean 107 KB cases, ph\u00e2n t\u00edch BM25 vs Dense:"
))

cells.append(code(
    'def check_hit(retriever, case):\n'
    '    if not case.get("expected_selectors"): return False\n'
    '    results = retriever.search(case["query"], top_k=5)\n'
    '    sources = {r.chunk.source for r in results}\n'
    '    return any(any(sel.split(":")[-1] in s for s in sources) for sel in case["expected_selectors"])\n\n'
    'dense_saves, bm25_saves, both_miss, both_hit = [], [], [], []\n'
    'for c in kb_cases:\n'
    '    b, d = check_hit(bm25, c), check_hit(dense, c)\n'
    '    if b and d: both_hit.append(c)\n'
    '    elif d and not b: dense_saves.append(c)\n'
    '    elif b and not d: bm25_saves.append(c)\n'
    '    else: both_miss.append(c)\n\n'
    'print(f"C\u1ea3 hai hit:       {len(both_hit)}")\n'
    'print(f"Dense c\u1ee9u BM25:   {len(dense_saves)}")\n'
    'print(f"BM25 c\u1ee9u Dense:   {len(bm25_saves)}")\n'
    'print(f"C\u1ea3 hai miss:      {len(both_miss)}")\n\n'
    'venn = pd.DataFrame([{"": "Dense HIT", "BM25 HIT": len(both_hit), "BM25 MISS": len(dense_saves)},\n'
    '                      {"": "Dense MISS", "BM25 HIT": len(bm25_saves), "BM25 MISS": len(both_miss)}])\n'
    'display(venn.style.hide(axis="index").set_caption("Ma tr\u1eadn BM25 vs Dense (107 KB cases)"))'
))

cells.append(md("#### Dense c\u1ee9u \u0111\u01b0\u1ee3c m\u00e0 BM25 miss"))
cells.append(code(
    'if dense_saves:\n'
    '    ds = [{"Query": c["query"][:50], "Noise": c.get("noise_type","clean"),\n'
    '           "Expected": c["expected_selectors"][0].split(":")[-1]} for c in dense_saves[:8]]\n'
    '    display(pd.DataFrame(ds).style.hide(axis="index").set_caption(f"Dense c\u1ee9u BM25 ({len(dense_saves)} cases)"))\n'
    'else: print("Kh\u00f4ng c\u00f3")'
))

cells.append(md("#### BM25 c\u1ee9u \u0111\u01b0\u1ee3c m\u00e0 Dense miss"))
cells.append(code(
    'if bm25_saves:\n'
    '    bs = [{"Query": c["query"][:50], "Noise": c.get("noise_type","clean"),\n'
    '           "Expected": c["expected_selectors"][0].split(":")[-1]} for c in bm25_saves[:8]]\n'
    '    display(pd.DataFrame(bs).style.hide(axis="index").set_caption(f"BM25 c\u1ee9u Dense ({len(bm25_saves)} cases)"))\n'
    '    noise_types = Counter(c.get("noise_type","clean") for c in bm25_saves)\n'
    '    print(f"\\nPh\u00e2n lo\u1ea1i: {dict(noise_types)}")\n'
    '    print("=> BM25 c\u1ee9u Dense ch\u1ee7 y\u1ebfu l\u00e0 noisy cases (nh\u1edd normalize built-in)")\n'
    'else: print("Kh\u00f4ng c\u00f3")'
))

# S6.4 Error analysis — hard cases
cells.append(md(
    "### 6.4 Error analysis \u2014 c\u00e1c case kh\u00f3\n\n"
    "Ph\u00e2n t\u00edch c\u00e1c cases m\u00e0 **c\u1ea3 3 methods \u0111\u1ec1u miss** \u2014 t\u1ea1i sao?"
))

cells.append(code(
    'hybrid_saves = [c for c in both_miss if check_hit(hybrid, c)]\n'
    'still_miss = [c for c in both_miss if not check_hit(hybrid, c)]\n\n'
    'print(f"C\u1ea3 BM25+Dense miss: {len(both_miss)}")\n'
    'print(f"Hybrid c\u1ee9u:         {len(hybrid_saves)}")\n'
    'print(f"C\u1ea3 3 miss:          {len(still_miss)}")\n\n'
    '# Deduplicate: group by base query\n'
    'base_queries = {}\n'
    'for c in still_miss:\n'
    '    base = c.get("parent_case_id", c["case_id"])\n'
    '    base_queries.setdefault(base, []).append(c)\n'
    'print(f"\\nTh\u1ef1c t\u1ebf l\u00e0 {len(base_queries)} queries g\u1ed1c + noisy variants c\u1ee7a ch\u00fang:")\n\n'
    'for base_id, cases in base_queries.items():\n'
    '    c0 = cases[0]\n'
    '    expected_file = c0["expected_selectors"][0].split(":")[-1]\n'
    '    print(f"\\n  Query g\u1ed1c: {[x for x in cases if x.get(\'noise_type\') in (None, \'clean\', \'vocab-mismatch\')][0][\'query\'] if any(x.get(\'noise_type\') in (None, \'clean\', \'vocab-mismatch\') for x in cases) else cases[0][\'query\']}")\n'
    '    print(f"  Expected:   {expected_file}")\n'
    '    print(f"  Variants:   {len(cases)} cases ({\', \'.join(c.get(\'noise_type\',\'clean\') for c in cases)})")\n'
    '    # Show what BM25 returned for first case\n'
    '    results = bm25.search(cases[0]["query"], top_k=3)\n'
    '    top = [f"{r.chunk.source}" for r in results[:3]]\n'
    '    print(f"  BM25 top-3: {\", \".join(top)}")'
))

cells.append(md(
    "#### T\u1ea1i sao c\u1ea3 3 miss?\n\n"
    "8 cases miss th\u1ef1c ch\u1ea5t l\u00e0 **v\u00e0i queries g\u1ed1c** + c\u00e1c noisy variants c\u1ee7a ch\u00fang.\n"
    "Nguy\u00ean nh\u00e2n ch\u00ednh:\n\n"
    "1. **T\u1eeb \u0111\u1ed3ng ngh\u0129a ti\u1ebfng Vi\u1ec7t:** \"\u0111\u1eadu ph\u1ed9ng\" v\u00e0 \"l\u1ea1c\" l\u00e0 c\u00f9ng m\u1ed9t th\u1ee9 nh\u01b0ng\n"
    "   BM25 kh\u00f4ng match, v\u00e0 E5 (train \u0111a ng\u00f4n ng\u1eef) c\u0169ng kh\u00f4ng n\u1eafm \u0111\u01b0\u1ee3c.\n"
    "2. **Noisy + semantic gap:** Kh\u00f4ng d\u1ea5u (\"dau phong\") l\u00e0m m\u1ea5t c\u1ea3 lexical l\u1eabn semantic signal.\n"
    "3. **Vocab mismatch s\u00e2u:** \"h\u1ee7y \u0111\u01a1n\" vs \"Thay \u0110\u1ed5i Order\" \u2014 kh\u00e1c ho\u00e0n to\u00e0n v\u1ec1 t\u1eeb.\n\n"
    "\u0110\u00e2y l\u00e0 gi\u1edbi h\u1ea1n c\u1ee7a retrieval \u2014 c\u1ea7n LLM ho\u1eb7c knowledge graph \u0111\u1ec3 hi\u1ec3u\n"
    "\"\u0111\u1eadu ph\u1ed9ng = l\u1ea1c\" ho\u1eb7c \"h\u1ee7y \u0111\u01a1n \u2248 thay \u0111\u1ed5i order\"."
))

# S6.5 Dense + Normalize
cells.append(md(
    "### 6.5 Th\u00ed nghi\u1ec7m: Normalize gi\u00fap Dense kh\u00f4ng?\n\n"
    "Dense E5 ch\u1ec9 25% tr\u00ean noisy. H\u1ec7 th\u1ed1ng c\u00f3 2 h\u00e0m normalize:\n\n"
    "| H\u00e0m | Thao t\u00e1c | Ph\u00f9 h\u1ee3p |\n"
    "|---|---|---|\n"
    "| `normalize_query_text()` | **Strip d\u1ea5u**, s\u1eeda teencode, emoji | BM25 (lexical) |\n"
    "| `normalize_vietnamese()` | **Gi\u1eef d\u1ea5u**, ch\u1ec9 s\u1eeda teencode | Dense (semantic) |\n\n"
    "**T\u1ea1i sao kh\u00f4ng d\u00f9ng `normalize_query_text()` cho Dense?**\n"
    "V\u00ec n\u00f3 strip d\u1ea5u \u2192 query th\u00e0nh text kh\u00f4ng d\u1ea5u \u2192 E5 (train tr\u00ean text c\u00f3 d\u1ea5u) hi\u1ec3u sai.\n"
    "Nh\u01b0ng `normalize_vietnamese()` c\u0169ng c\u00f3 h\u1ea1n ch\u1ebf \u2014 xem k\u1ebft qu\u1ea3:"
))

cells.append(code(
    'from app.rag.vietnamese_normalizer import normalize_vietnamese\n'
    'from app.rag.retriever import RetrievedChunk\n\n'
    'class NormalizedDense:\n'
    '    def __init__(self, dense_ret):\n'
    '        self._d = dense_ret\n'
    '    def search(self, query, top_k=5, **kw):\n'
    '        return self._d.search(normalize_vietnamese(query), top_k=top_k, **kw)\n\n'
    'dense_norm = NormalizedDense(dense)\n'
    'hybrid_norm = HybridRrfRetriever([bm25, dense_norm])\n\n'
    '# Full comparison\n'
    'configs = {"BM25": bm25, "Dense": dense, "Dense+norm_vi": dense_norm,\n'
    '           "Hybrid": hybrid, "Hybrid+norm_vi": hybrid_norm}\n\n'
    'rows = []\n'
    'for gname, gcases in [("Clean KB", clean_kb), ("Noisy", noisy), ("Vocab", vocab)]:\n'
    '    n = len(gcases)\n'
    '    row = {"T\u1eadp": f"{gname} ({n})"}\n'
    '    for cname, cret in configs.items():\n'
    '        h1, h5 = eval_hits(cret, gcases)\n'
    '        row[cname] = f"{h5}/{n} ({h5/n:.0%})"\n'
    '    rows.append(row)\n'
    'display(pd.DataFrame(rows).style.hide(axis="index").set_caption(\n'
    '    "Impact c\u1ee7a normalize_vietnamese() l\u00ean Dense"))'
))

cells.append(md(
    "#### T\u1ea1i sao Dense+norm_vi gi\u1ea3m tr\u00ean Clean?\n\n"
    "`normalize_vietnamese()` thay \u0111\u1ed5i m\u1ed9t s\u1ed1 t\u1eeb trong query **c\u0169ng nh\u01b0 d\u1ea5u c\u00e2u** \u2192\n"
    "embedding thay \u0111\u1ed5i \u2192 cosine similarity gi\u1ea3m.\n\n"
    "**Quan tr\u1ecdng:** Documents \u0111\u01b0\u1ee3c encode **kh\u00f4ng normalize**.\n"
    "N\u1ebfu normalize query nh\u01b0ng kh\u00f4ng normalize document \u2192 **embedding space mismatch**.\n\n"
    "**K\u1ebft lu\u1eadn:** Normalize cho Dense ch\u1ec9 n\u00ean \u00e1p d\u1ee5ng **c\u00f3 \u0111i\u1ec1u ki\u1ec7n** (khi detect query l\u00e0 noisy),\n"
    "kh\u00f4ng \u00e1p d\u1ee5ng m\u1eb7c \u0111\u1ecbnh. Ho\u1eb7c c\u1ea7n normalize **c\u1ea3 documents l\u1eabn queries**."
))

# S6.6 BM25 preprocessing
cells.append(md(
    "### 6.6 Impact Normalize v\u00e0 Variants tr\u00ean BM25"
))

cells.append(code(
    'import math\n'
    'from app.rag.knowledge_base import KnowledgeChunk\n'
    'import re as _re\n\n'
    'class RawBM25:\n'
    '    def __init__(self, chunks):\n'
    '        self._chunks = chunks\n'
    '        self._tok = [c.content.lower().split() for c in chunks]\n'
    '        self._N = len(chunks)\n'
    '        self._avgdl = sum(len(t) for t in self._tok) / max(self._N, 1)\n'
    '        self._df = {}\n'
    '        for tokens in self._tok:\n'
    '            for t in set(tokens): self._df[t] = self._df.get(t, 0) + 1\n'
    '    def search(self, query, top_k=5, **kw):\n'
    '        qtok = query.lower().split()\n'
    '        scores = []\n'
    '        for chunk, dtok in zip(self._chunks, self._tok):\n'
    '            s = 0.0\n'
    '            dl = len(dtok)\n'
    '            for qt in qtok:\n'
    '                tf = dtok.count(qt)\n'
    '                df = self._df.get(qt, 0)\n'
    '                if tf == 0 or df == 0: continue\n'
    '                idf = math.log((self._N - df + 0.5)/(df + 0.5) + 1)\n'
    '                s += idf * (tf*2.0)/(tf + 1.2*(1-0.75+0.75*dl/self._avgdl))\n'
    '            if s > 0: scores.append(RetrievedChunk(chunk=chunk, score=s))\n'
    '        scores.sort(key=lambda x: x.score, reverse=True)\n'
    '        return scores[:top_k]\n\n'
    'bm25_raw = RawBM25(kb_chunks)\n'
    'stripped = [KnowledgeChunk(source=c.source, title=c.title,\n'
    '    content=_re.sub(r"question_variants:.*", "", c.content),\n'
    '    tags=c.tags, chunk_id=c.chunk_id, risk_tier=c.risk_tier) for c in kb_chunks]\n'
    'bm25_no_var = BM25Retriever(stripped)\n\n'
    'bm25_cfgs = {"BM25 production": bm25, "BM25 (no normalize)": bm25_raw, "BM25 (no variants)": bm25_no_var}\n'
    'rows = []\n'
    'for gname, gcases in [("Clean KB", clean_kb), ("Noisy", noisy), ("Vocab", vocab)]:\n'
    '    n = len(gcases)\n'
    '    row = {"T\u1eadp": f"{gname} ({n})"}\n'
    '    for cname, cret in bm25_cfgs.items():\n'
    '        h1, h5 = eval_hits(cret, gcases)\n'
    '        row[cname] = f"{h5}/{n} ({h5/n:.0%})"\n'
    '    rows.append(row)\n'
    'display(pd.DataFrame(rows).style.hide(axis="index").set_caption(\n'
    '    "Impact Normalize v\u00e0 Variants tr\u00ean BM25"))'
))

# S6.7 Latency
cells.append(md("### 6.7 Latency"))

cells.append(code(
    'test_qs = ["nh\u00e0 h\u00e0ng c\u00f3 wifi kh\u00f4ng?", "m\u00f3n n\u00e0o kh\u00f4ng cay?",\n'
    '           "thanh to\u00e1n b\u1eb1ng th\u1ebb?", "c\u00f3 combo cho 4 ng\u01b0\u1eddi?", "h\u1ee7y m\u00f3n nh\u01b0 n\u00e0o?"]\n\n'
    'latency = {}\n'
    'for name, ret in methods.items():\n'
    '    times = []\n'
    '    for q in test_qs:\n'
    '        t0 = time.perf_counter()\n'
    '        ret.search(q, top_k=5)\n'
    '        times.append((time.perf_counter()-t0)*1000)\n'
    '    latency[name] = times\n\n'
    'lat_df = pd.DataFrame([{"Ph\u01b0\u01a1ng ph\u00e1p": n, "Min": f"{min(t):.1f}ms",\n'
    '    "Avg": f"{sum(t)/len(t):.1f}ms", "Max": f"{max(t):.1f}ms"}\n'
    '    for n, t in latency.items()])\n'
    'display(lat_df.style.hide(axis="index").set_caption("Latency per query"))\n\n'
    'fig, ax = plt.subplots(figsize=(6, 4))\n'
    'avg = [sum(t)/len(t) for t in latency.values()]\n'
    'bars = ax.bar(latency.keys(), avg, color=["#3b82f6","#8b5cf6","#10b981"])\n'
    'for b, v in zip(bars, avg):\n'
    '    ax.text(b.get_x()+b.get_width()/2., b.get_height()+0.3,\n'
    '            f"{v:.1f}ms", ha="center", fontsize=10)\n'
    'ax.set_ylabel("Avg latency (ms)")\n'
    'ax.set_title("Latency trung b\u00ecnh per query")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

# S6.8 Heatmap
cells.append(md("### 6.8 T\u1ed5ng h\u1ee3p \u2014 Heatmap"))

cells.append(code(
    'import matplotlib.colors as mcolors\n\n'
    '# Build heatmap data\n'
    'hm_methods = ["BM25", "Dense E5", "Hybrid RRF"]\n'
    'hm_groups = ["Clean KB", "Noisy", "Vocab mismatch"]\n'
    'hm_data = []\n'
    'for g in hm_groups:\n'
    '    row = []\n'
    '    gcases = {"Clean KB": clean_kb, "Noisy": noisy, "Vocab mismatch": vocab}[g]\n'
    '    for m in hm_methods:\n'
    '        _, h5 = eval_hits(methods[m], gcases)\n'
    '        row.append(h5 / len(gcases))\n'
    '    hm_data.append(row)\n\n'
    'fig, ax = plt.subplots(figsize=(7, 4))\n'
    'cmap = mcolors.LinearSegmentedColormap.from_list("", ["#fee2e2","#fef9c3","#dcfce7"])\n'
    'im = ax.imshow(hm_data, cmap=cmap, vmin=0.2, vmax=1.0, aspect="auto")\n\n'
    'ax.set_xticks(range(len(hm_methods)))\n'
    'ax.set_xticklabels(hm_methods)\n'
    'ax.set_yticks(range(len(hm_groups)))\n'
    'ax.set_yticklabels(hm_groups)\n\n'
    'for i in range(len(hm_groups)):\n'
    '    for j in range(len(hm_methods)):\n'
    '        ax.text(j, i, f"{hm_data[i][j]:.0%}", ha="center", va="center",\n'
    '                fontsize=14, fontweight="bold")\n\n'
    'ax.set_title("Hit@5 Heatmap \u2014 3 methods \\u00d7 3 t\u1eadp d\u1eef li\u1ec7u")\n'
    'plt.colorbar(im, ax=ax, label="Hit@5")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md("### 6.9 Export screening metrics (Part II → JSON)"))

cells.append(code(
    'import json\n'
    'from datetime import datetime, timezone\n\n'
    'h1, h5 = eval_hits(hybrid, kb_cases)\n'
    'hit5_overall = h5 / len(kb_cases) if kb_cases else 0.0\n'
    'by_group = {}\n'
    'for gname, gcases in [("clean_kb", clean_kb), ("noisy", noisy), ("vocab", vocab)]:\n'
    '    _, g5 = eval_hits(hybrid, gcases)\n'
    '    by_group[gname] = {"hit5": g5 / len(gcases) if gcases else 0.0, "n": len(gcases)}\n'
    'screening = {\n'
    '    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),\n'
    '    "method": "hybrid_rrf",\n'
    '    "hit5_overall": hit5_overall,\n'
    '    "hit5_by_group": by_group,\n'
    '    "eval_case_count": len(kb_cases),\n'
    '}\n'
    'screen_path = AI_ROOT / "evaluation" / "results" / "notebook_retrieval_screening.json"\n'
    'screen_path.parent.mkdir(parents=True, exist_ok=True)\n'
    'screen_path.write_text(json.dumps(screening, ensure_ascii=False, indent=2), encoding="utf-8")\n'
    'print(f"Hybrid Hit@5 overall: {hit5_overall:.1%} ({h5}/{len(kb_cases)} cases)")\n'
    'print(f"Saved {screen_path}")'
))

cells.append(md(HIT5_SCREENING_VS_RELEASE_MD))

# ===== S7 CONCLUSION =====
cells.append(md(
    "---\n"
    "## K\u1ebft lu\u1eadn Ph\u1ea7n II\n\n"
    "### L\u01b0u \u00fd v\u1ec1 d\u1eef li\u1ec7u v\u00e0 th\u1ed1ng k\u00ea\n\n"
    "- To\u00e0n b\u1ed9 k\u1ebft qu\u1ea3 tr\u00ean **b\u1ed9 d\u1eef li\u1ec7u t\u1ef1 x\u00e2y** (26 files KB, 107 eval cases).\n"
    "- V\u1edbi n nh\u1ecf (vocab=19, clean=35), kh\u00e1c bi\u1ec7t nh\u1ecf c\u00f3 th\u1ec3 do ng\u1eabu nhi\u00ean.\n"
    "- K\u1ebft qu\u1ea3 kh\u00f4ng generalize \u2014 nh\u01b0ng ph\u01b0\u01a1ng ph\u00e1p \u0111\u00e1nh gi\u00e1 c\u00f3 th\u1ec3 t\u00e1i s\u1eed d\u1ee5ng.\n\n"
    "### Nh\u1eefng \u0111i\u1ec1u \u0111\u00e3 ch\u1ee9ng minh\n\n"
    "1. **Kh\u00f4ng c\u00f3 silver bullet** \u2014 m\u1ed7i method c\u00f3 th\u1ebf m\u1ea1nh ri\u00eang:\n"
    "   - BM25: m\u1ea1nh nh\u1ea5t noisy (89%) nh\u1edd normalize\n"
    "   - Dense: m\u1ea1nh nh\u1ea5t clean (100%) v\u00e0 vocab (89%) nh\u1edd semantic\n"
    "   - Hybrid: c\u00e2n b\u1eb1ng nh\u1ea5t\n\n"
    "2. **Normalize ph\u1ea3i ph\u00f9 h\u1ee3p lo\u1ea1i retriever:**\n"
    "   - BM25: `normalize_query_text()` (strip d\u1ea5u) \u2192 +49% noisy\n"
    "   - Dense: `normalize_vietnamese()` (gi\u1eef d\u1ea5u) \u2192 c\u1ea3i thi\u1ec7n noisy nh\u01b0ng gi\u1ea3m clean\n"
    "   - Dense normalize ch\u1ec9 n\u00ean \u00e1p d\u1ee5ng khi detect query noisy\n\n"
    "3. **False positive l\u00e0 v\u1ea5n \u0111\u1ec1 chung** \u2014 c\u1ea3 3 methods \u0111\u1ec1u tr\u1ea3 v\u1ec1 k\u1ebft qu\u1ea3\n"
    "   cho negative cases. C\u1ea7n guardrails \u1edf t\u1ea7ng LLM.\n\n"
    "### Trade-off\n\n"
    "| Ti\u00eau ch\u00ed | BM25 | Dense E5 | Hybrid RRF |\n"
    "|---|---|---|---|\n"
    "| **Clean** | 91% | **100%** | **100%** |\n"
    "| **Noisy** | **89%** | 25% | 74% |\n"
    "| **Vocab** | 79% | **89%** | **89%** |\n"
    "| **Latency** | ~3ms | ~17ms | ~26ms |\n"
    "| **GPU** | Kh\u00f4ng | Kh\u00f4ng (CPU \u0111\u1ee7) | Kh\u00f4ng |\n\n"
    "### Khuy\u1ebfn ngh\u1ecb\n\n"
    "- **Production:** Hybrid RRF (BM25 + normalize + Dense E5, encoder **`e5_small`**)\n"
    "- **Fallback:** BM25 + normalize + variants (88% t\u1ed5ng, 3ms latency)\n"
    "- **C\u1ea3i thi\u1ec7n ti\u1ebfp:** Th\u00eam eval cases t\u1eeb traffic th\u1eadt, th\u1eed fine-tune E5\n\n"
    "> **Kết luận:** Trên bộ dữ liệu tự xây, kết hợp là chiến lược tốt nhất.\n"
    "> Mỗi phương pháp bù nhược điểm cho nhau — BM25 cứu noisy, Dense cứu semantic.\n\n"
    "> **Chốt báo cáo:** cuối notebook — **§18 Đưa vào production** (tính năng đã áp dụng + stack vận hành)."
))

# ===== WRITE =====
nb.cells = cells
nbf.write(nb, str(nb_path))
print(f"Wrote {nb_path} ({len(cells)} cells)")
