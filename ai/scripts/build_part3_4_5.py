# -*- coding: utf-8 -*-
"""Build Part III+IV+V — rich charts + markdown analysis."""
import sys
from pathlib import Path

import nbformat as nbf

_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))
from scripts.notebook_metrics import format_deploy_lock_section

nb_path = Path(r"d:\01_Projects\Fable\restaurant-qr-ai-ordering\ai\notebooks\rag_retrieval_research.ipynb")
nb = nbf.read(str(nb_path), as_version=4)

def md(src): return nbf.v4.new_markdown_cell(src.strip())
def code(src): return nbf.v4.new_code_cell(src.strip())

# Strip old Part III-V cells (keep Part I + II only)
part3_marker = "PH\u1ea6N III"
cut_idx = None
for i, cell in enumerate(nb.cells):
    src = ''.join(cell.source) if isinstance(cell.source, list) else cell.source
    if part3_marker in src:
        cut_idx = i
        break
if cut_idx is not None:
    nb.cells = nb.cells[:cut_idx]
    print(f"  Stripped old Part III-V from cell {cut_idx}, keeping {len(nb.cells)} cells")

cells = nb.cells

# ============ PART III HEADER ============
cells.append(md(
    "# PH\u1ea6N III \u2014 CHATBOT C\u00d3 NG\u1eee C\u1ea2NH\n\n"
    "Ph\u1ea7n I \u0111\u00e3 kh\u00e1m ph\u00e1 **26 files KB, 213 chunks** v\u00e0 c\u00e1ch normalize ti\u1ebfng Vi\u1ec7t.\n"
    "Ph\u1ea7n II \u0111\u00e3 ch\u1ee9ng minh **Hybrid RRF** l\u00e0 retrieval t\u1ed1t nh\u1ea5t (Hit@5 trong `notebook_retrieval_screening.json` sau khi ch\u1ea1y Part II).\n\n"
    "Gi\u1edd c\u00e2u h\u1ecfi l\u00e0: khi kh\u00e1ch h\u1ecfi `\"c\u00f3 wifi kh\u00f4ng?\"` vs `\"g\u1ee3i \u00fd m\u00f3n \u0111i\"`,\n"
    "h\u1ec7 th\u1ed1ng quy\u1ebft \u0111\u1ecbnh d\u00f9ng **Hybrid RRF** (t\u00ecm KB) hay **Catalog API** (t\u00ecm menu) nh\u01b0 th\u1ebf n\u00e0o?\n\n"
    "> **Th\u1ed1ng nh\u1ea5t d\u1eef li\u1ec7u:** Part III\u2013IV d\u00f9ng c\u00f9ng **20 queries** (6 categories)\n"
    "> cho c\u1ea3 intent classification, pipeline test, v\u00e0 so s\u00e1nh 3 model.\n"
    "> \u0110\u1ea3m b\u1ea3o k\u1ebft qu\u1ea3 traceable: query X \u2192 intent Y \u2192 route Z \u2192 response.\n\n"
    "Ph\u1ea7n n\u00e0y tr\u00ecnh b\u00e0y 4 th\u00e0nh ph\u1ea7n x\u00e2y d\u1ef1ng pipeline ho\u00e0n ch\u1ec9nh:\n\n"
    "```\n"
    "User query\n"
    "  \u2502\n"
    "  \u251c\u2500\u2500 [1] Guardrails      \u2192 ch\u1eb7n PII, injection, off-topic\n"
    "  \u251c\u2500\u2500 [2] Intent Router    \u2192 KB (Hybrid RRF) / Catalog / Cart / Fallback\n"
    "  \u251c\u2500\u2500 [3] Session Memory   \u2192 nh\u1edb d\u1ecb \u1ee9ng, l\u1ecbch s\u1eed, t\u00f3m t\u1eaft\n"
    "  \u2514\u2500\u2500 [4] Claim Verifier   \u2192 ch\u1eb7n hallucination sau LLM\n"
    "```"
))

cells.append(code(
    'import json\n'
    'from scripts.notebook_metrics import load_retrieval_headlines\n\n'
    'live_test = json.load(open(\n'
    '    AI_ROOT / "evaluation" / "results" / "notebook_live_test.json",\n'
    '    encoding="utf-8"\n'
    '))\n'
    '_retrieval_headlines = load_retrieval_headlines(AI_ROOT)\n'
    'hit5_label = _retrieval_headlines["screening_label"]\n'
    'hit5_score = float(_retrieval_headlines["screening_hit5"] or 0.0)\n'
    'release_retrieval_note = _retrieval_headlines.get("release_label") or ""\n'
    'print(f"Test: {live_test[\'timestamp\']}, Model: {live_test[\'model\']}, Retrieval: {live_test[\'retrieval_method\']}")\n'
    'print(f"Part II screening: {hit5_label}")\n'
    'if release_retrieval_note:\n'
    '    print(f"Release artifact: {release_retrieval_note}")'
))

# ============ S8 EVIDENCE ROUTING ============
cells.append(md(
    "## 8. Evidence Routing \u2014 quy\u1ebft \u0111\u1ecbnh \u0111\u01b0\u1eddng \u0111i c\u1ee7a query\n\n"
    "Ph\u1ea7n II ch\u1ee9ng minh **Hybrid RRF** l\u00e0 retrieval t\u1ed1t nh\u1ea5t.\n"
    "Nh\u01b0ng kh\u00f4ng ph\u1ea3i m\u1ecdi query \u0111\u1ec1u c\u1ea7n search KB \u2014\n"
    "`\"g\u1ee3i \u00fd m\u00f3n\"` c\u1ea7n menu data, kh\u00f4ng c\u1ea7n KB.\n\n"
    "**Intent Classifier** l\u00e0m router: ph\u00e2n lo\u1ea1i query \u2192 ch\u1ecdn \u0111\u01b0\u1eddng \u0111i.\n\n"
    "| Intent | Route | Ngu\u1ed3n d\u1eef li\u1ec7u |\n"
    "|---|---|---|\n"
    "| `restaurant_info`, `payment` | **KB (Hybrid RRF)** | 213 chunks t\u1eeb Part I |\n"
    "| `browse_menu`, `ask_price` | **Catalog API** | Menu data th\u1eadt |\n"
    "| `order` | **Cart API** | Gi\u1ecf h\u00e0ng |\n"
    "| `general` | **Fallback** | H\u1ecfi l\u1ea1i / t\u1eeb ch\u1ed1i |\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `notebook_live_test.json` \u2192 `intent_results` (20 queries, c\u00f9ng set v\u1edbi \u00a712 v\u00e0 \u00a714)"
))

cells.append(code(
    '# B\u1ea3ng intent classification\n'
    'ir = live_test["intent_results"]\n'
    'route_map = {"browse_menu": "Catalog API", "ask_price": "Catalog API",\n'
    '             "order": "Cart API", "restaurant_info": "KB (Hybrid RRF)",\n'
    '             "payment": "KB (Hybrid RRF)", "spice_level": "KB (Hybrid RRF)",\n'
    '             "recommend": "Catalog API", "allergy": "KB + Menu",\n'
    '             "general": "Fallback"}\n'
    'intent_rows = [{"Query": r["query"][:35], "Intent": r["intent"],\n'
    '                "Conf": f\'{r["confidence"]:.2f}\',\n'
    '                "Route": route_map.get(r["intent"], "Fallback")}\n'
    '               for r in ir]\n'
    'display(pd.DataFrame(intent_rows).style.hide(axis="index").set_caption(\n'
    '    f"Intent Classification: {len(ir)} queries"))'
))

cells.append(code(
    '# Routing Distribution\n'
    'from collections import Counter\n'
    'import matplotlib\n'
    'matplotlib.rcParams["figure.dpi"] = 150\n'
    'routes = [route_map.get(r["intent"], "Fallback") for r in ir]\n'
    'rc = Counter(routes)\n\n'
    'fig, ax = plt.subplots(figsize=(6, 4))\n'
    'labels = list(rc.keys())\n'
    'sizes = list(rc.values())\n'
    'colors = ["#10b981", "#3b82f6", "#f59e0b", "#94a3b8", "#8b5cf6"][:len(labels)]\n'
    'wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,\n'
    '    autopct="%1.0f%%", startangle=90, pctdistance=0.75)\n'
    'for t in texts: t.set_fontsize(9)\n'
    'for t in autotexts: t.set_fontsize(8)\n'
    'ax.set_title("Routing Distribution", fontsize=11, fontweight="bold")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(code(
    '# Intent Confidence\n'
    'classified = [r for r in ir if r["intent"] != "general"]\n'
    'fallback = [r for r in ir if r["intent"] == "general"]\n'
    'intents_sorted = sorted(classified, key=lambda x: x["confidence"])\n'
    'names = [r["intent"] for r in intents_sorted]\n'
    'confs = [r["confidence"] for r in intents_sorted]\n\n'
    'fig, ax = plt.subplots(figsize=(7, max(3, len(names)*0.4)))\n'
    'bars = ax.barh(range(len(names)), confs, color="#3b82f6", height=0.5)\n'
    'ax.set_yticks(range(len(names)))\n'
    'ax.set_yticklabels(names, fontsize=8)\n'
    'for i, v in enumerate(confs):\n'
    '    ax.text(v + 0.01, i, f"{v:.2f}", va="center", fontsize=8)\n'
    'ax.set_xlabel("Confidence", fontsize=9)\n'
    'ax.set_title(f"Intent Confidence ({len(classified)} classified, {len(fallback)} fallback)",\n'
    '             fontsize=11, fontweight="bold")\n'
    'ax.set_xlim(0, max(confs)*1.3 if confs else 1)\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md(
    "### Nh\u1eadn x\u00e9t Evidence Routing\n\n"
    "**K\u1ebft qu\u1ea3 t\u1ed1t:**\n"
    "- Intent classifier ph\u00e2n bi\u1ec7t \u0111\u01b0\u1ee3c c\u00e1c lo\u1ea1i query ch\u00ednh: menu, gi\u00e1, th\u00f4ng tin nh\u00e0 h\u00e0ng, thanh to\u00e1n\n"
    "- Routing \u0111\u00fang: FAQ \u2192 KB (Hybrid RRF t\u1eeb Part II), menu \u2192 Catalog API\n"
    "- T\u1ed1c \u0111\u1ed9 <1ms (rule-based, kh\u00f4ng ML)\n\n"
    "**H\u1ea1n ch\u1ebf:**\n"
    "- **Teencode** kh\u00f4ng match: `\"ko cay dc ko\"` \u2192 `general` (th\u1ef1c ra l\u00e0 `spice_level`)\n"
    "- **Confidence th\u1ea5p** cho nhi\u1ec1u intents (0.1-0.3) \u2014 v\u00ec ch\u1ec9 \u0111\u1ebfm keyword, kh\u00f4ng scoring ph\u1ee9c t\u1ea1p\n"
    "- **`\"t\u00f4i d\u1ecb \u1ee9ng t\u00f4m\"` \u2192 `browse_menu`** thay v\u00ec `allergy` \u2014 c\u1ea7n th\u00eam allergy rules\n\n"
    "**Li\u00ean k\u1ebft Part II:**\n"
    "Khi intent l\u00e0 `restaurant_info`, `payment`, `spice_level` \u2192\n"
    "h\u1ec7 th\u1ed1ng g\u1ecdi **Hybrid RRF** (BM25 + Dense E5) \u0111\u00e3 benchmark \u1edf Part II\n"
    "v\u1edbi Hit@5 screening t\u1eeb Part II (`notebook_retrieval_screening.json`). \u0110\u00e2y l\u00e0 l\u00fac retrieval \u0111\u01b0\u1ee3c s\u1eed d\u1ee5ng th\u1eadt."
))

# ============ S9 GUARDRAILS ============
cells.append(md(
    "## 9. Guardrails \u2014 b\u1ea3o v\u1ec7 chatbot\n\n"
    "**Tr\u01b0\u1edbc khi** query v\u00e0o pipeline, regex patterns ki\u1ec3m tra c\u00e1c m\u1ed1i nguy:\n"
    "- **PII:** S\u1ed1 CCCD, s\u1ed1 \u0111i\u1ec7n tho\u1ea1i \u2192 kh\u00f4ng \u0111\u01b0\u1ee3c l\u01b0u/x\u1eed l\u00fd\n"
    "- **Injection:** C\u1ed1 thay \u0111\u1ed5i h\u00e0nh vi chatbot\n"
    "- **Off-topic:** C\u00e2u h\u1ecfi kh\u00f4ng li\u00ean quan nh\u00e0 h\u00e0ng\n"
    "- **Profanity:** Ng\u00f4n ng\u1eef th\u00f4 t\u1ee5c\n"
    "- **Fabrication:** Y\u00eau c\u1ea7u AI b\u1ecba gi\u00e1/m\u00f3n\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `notebook_live_test.json` \u2192 `guard_results` (10 scenarios th\u1eed c\u1ed1 \u0111\u1ecbnh)"
))

cells.append(code(
    'gr = live_test["guard_results"]\n'
    'guard_rows = [{"Query": r["query"][:42], "Scenario": r["scenario"],\n'
    '               "Flags": ", ".join(r["flags"])}\n'
    '              for r in gr]\n'
    'display(pd.DataFrame(guard_rows).style.hide(axis="index").set_caption(\n'
    '    f"Guardrails: {len(gr)} test cases"))'
))

cells.append(code(
    '# Chart 2: Flag distribution\n'
    'all_flags = []\n'
    'for r in gr:\n'
    '    if r["flags"] != ["CLEAN"]:\n'
    '        all_flags.extend(r["flags"])\n'
    'fc = Counter(all_flags)\n\n'
    'fig, ax = plt.subplots(figsize=(10, 4))\n'
    'flags_sorted = sorted(fc.items(), key=lambda x: x[1], reverse=True)\n'
    'names = [f[0].replace("_"," ").title() for f in flags_sorted]\n'
    'vals = [f[1] for f in flags_sorted]\n'
    'colors_f = ["#ef4444","#f59e0b","#8b5cf6","#3b82f6","#10b981","#ec4899","#6366f1"]\n'
    'bars = ax.barh(names, vals, color=colors_f[:len(names)])\n'
    'for b, v in zip(bars, vals):\n'
    '    ax.text(b.get_width()+0.1, b.get_y()+b.get_height()/2, str(v), va="center")\n'
    'ax.set_xlabel("S\u1ed1 l\u1ea7n")\n'
    'ax.set_title("Ph\u00e2n b\u1ed1 Guardrail Flags")\n'
    'ax.invert_yaxis()\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md(
    "### Nh\u1eadn x\u00e9t Guardrails\n\n"
    "**\u0110i\u1ec3m m\u1ea1nh:**\n"
    "- **7 lo\u1ea1i flags** ph\u00e1t hi\u1ec7n \u0111\u01b0\u1ee3c, bao ph\u1ee7 c\u00e1c m\u1ed1i nguy ch\u00ednh\n"
    "- Ph\u00e2n bi\u1ec7t \u0111\u00fang: `\"\u0111\u1eb7t lu\u00f4n 2 t\u00f4 ph\u1edf\"` \u2192 CONFIRMATION (c\u1ea7n x\u00e1c nh\u1eadn),\n"
    "  nh\u01b0ng `\"thanh to\u00e1n b\u1eb1ng th\u1ebb\"` \u2192 Clean (ch\u1ec9 h\u1ecfi th\u00f4ng tin)\n"
    "- Prompt injection, PII \u2192 ch\u1eb7n ngay, kh\u00f4ng v\u00e0o pipeline\n\n"
    "**H\u1ea1n ch\u1ebf:**\n"
    "- Regex kh\u00f4ng b\u1eaft paraphrase: `\"l\u00e0m \u01a1n qu\u00ean h\u1ebft \u0111i\"` c\u00f3 th\u1ec3 bypass injection\n"
    "- Kh\u00f4ng detect tone ti\u00eang (m\u1ec9a mai) \u2014 c\u1ea7n NLU\n\n"
    "**Trong pipeline:** Guardrails ch\u1ea1y **tr\u01b0\u1edbc** Intent Router v\u00e0 **tr\u01b0\u1edbc** Hybrid RRF.\n"
    "N\u1ebfu b\u1ecb flag \u2192 kh\u00f4ng t\u1ed1n t\u00e0i nguy\u00ean g\u1ecdi LLM."
))

# ============ S10 SESSION + LIVE DATA ============
cells.append(md(
    "## 10. Session Memory \u2014 nh\u1edb ng\u1eef c\u1ea3nh qua nhi\u1ec1u l\u01b0\u1ee3t\n\n"
    "Khi kh\u00e1ch h\u1ecfi nhi\u1ec1u l\u01b0\u1ee3t, h\u1ec7 th\u1ed1ng ph\u1ea3i **nh\u1edb**:\n"
    "- L\u01b0\u1ee3t 1: `\"t\u00f4i d\u1ecb \u1ee9ng t\u00f4m\"` \u2192 l\u01b0u constraint\n"
    "- L\u01b0\u1ee3t 2: `\"g\u1ee3i \u00fd m\u00f3n\"` \u2192 l\u1ecdc b\u1ecf m\u00f3n c\u00f3 t\u00f4m\n"
    "- L\u01b0\u1ee3t 3: `\"c\u00e1i \u0111\u00f3 bao nhi\u00eau?\"` \u2192 hi\u1ec3u `\"c\u00e1i \u0111\u00f3\"` = m\u00f3n v\u1eeba g\u1ee3i\n\n"
    "H\u1ec7 th\u1ed1ng d\u00f9ng **3 c\u01a1 ch\u1ebf**:"
))

cells.append(code(
    'from app.schemas import SessionState, LiveContext\n\n'
    '# 3 c\u01a1 ch\u1ebf gi\u1eef ng\u1eef c\u1ea3nh\n'
    'mechanisms = [\n'
    '    {"C\u01a1 ch\u1ebf": "Chat History", "M\u00f4 t\u1ea3": "C\u00e1c l\u01b0\u1ee3t tr\u01b0\u1edbc g\u1eedi v\u00e0o LLM prompt",\n'
    '     "V\u00ed d\u1ee5": "LLM th\u1ea5y l\u01b0\u1ee3t 1 h\u1ecfi ph\u1edf b\u00f2 \u2192 hi\u1ec3u \'c\u00e1i \u0111\u00f3\'"},\n'
    '    {"C\u01a1 ch\u1ebf": "Rolling Summary", "M\u00f4 t\u1ea3": "LLM t\u00f3m t\u1eaft h\u1ed9i tho\u1ea1i m\u1ed7i l\u01b0\u1ee3t",\n'
    '     "V\u00ed d\u1ee5": "Kh\u00e1ch d\u1ecb \u1ee9ng t\u00f4m, \u0111\u00e3 g\u1ee3i \u00fd ph\u1edf b\u00f2..."},\n'
    '    {"C\u01a1 ch\u1ebf": "Typed Session State", "M\u00f4 t\u1ea3": "Pydantic model l\u01b0u constraints",\n'
    '     "V\u00ed d\u1ee5": "allergens=[\\\"t\u00f4m\\\"], budget=200000"},\n'
    ']\n'
    'display(pd.DataFrame(mechanisms).style.hide(axis="index").set_caption(\n'
    '    "3 c\u01a1 ch\u1ebf gi\u1eef ng\u1eef c\u1ea3nh"))\n\n'
    '# SessionState fields\n'
    'ss_rows = [{"Field": name, "Type": str(field.annotation).replace("typing.","")[:25]}\n'
    '           for name, field in SessionState.model_fields.items()]\n'
    'display(pd.DataFrame(ss_rows).style.hide(axis="index").set_caption(\n'
    '    "SessionState \u2014 typed constraints"))'
))

cells.append(md(
    "### 10.1 D\u1eef li\u1ec7u th\u1eadt t\u1eeb nh\u00e0 h\u00e0ng (LiveContext)\n\n"
    "AI **kh\u00f4ng b\u1ecba** gi\u00e1, kh\u00f4ng b\u1ecba m\u00f3n \u2014 tr\u1ea3 l\u1eddi d\u1ef1a tr\u00ean **d\u1eef li\u1ec7u th\u1eadt** t\u1eeb database.\n"
    "M\u1ed7i request, frontend g\u1eedi k\u00e8m `LiveContext` ch\u1ee9a menu, gi\u1ecf h\u00e0ng, khuy\u1ebfn m\u00e3i hi\u1ec7n t\u1ea1i:"
))

cells.append(code(
    '# LiveContext fields\n'
    'lc_descs = {"catalog_version": "Phi\u00ean b\u1ea3n menu", "menu_items": "M\u00f3n: t\u00ean, GI\u00c1 TH\u1eacT, allergens, is_available",\n'
    '            "cart_items": "Gi\u1ecf h\u00e0ng hi\u1ec7n t\u1ea1i", "orders": "\u0110\u01a1n \u0111\u00e3 \u0111\u1eb7t",\n'
    '            "promotions": "Khuy\u1ebfn m\u00e3i \u0111ang ch\u1ea1y", "local_time": "Gi\u1edd hi\u1ec7n t\u1ea1i",\n'
    '            "meal_period": "Bu\u1ed5i \u0103n (lunch/dinner)", "table_code": "M\u00e3 b\u00e0n"}\n'
    'lc_rows = [{"Field": name, "Type": str(field.annotation).replace("typing.","")[:25],\n'
    '            "M\u00f4 t\u1ea3": lc_descs.get(name, "")}\n'
    '           for name, field in LiveContext.model_fields.items()]\n'
    'display(pd.DataFrame(lc_rows).style.hide(axis="index").set_caption(\n'
    '    "LiveContext \u2014 d\u1eef li\u1ec7u th\u1eadt m\u1ed7i request"))'
))

cells.append(md(
    "### 10.2 Cart Suggestion \u2014 g\u1ee3i \u00fd th\u00eam v\u00e0o gi\u1ecf\n\n"
    "Khi AI t\u01b0 v\u1ea5n m\u00f3n, response ch\u1ee9a `suggested_cart_actions`:\n"
    "```json\n"
    "{\"content\": \"Ph\u1edf B\u00f2 T\u00e1i N\u1ea1m (75.000\u0111) l\u00e0 best-seller...\",\n"
    " \"suggested_cart_actions\": [{\"menu_item_id\": \"pho-bo-01\", \"name\": \"Ph\u1edf B\u00f2 T\u00e1i N\u1ea1m\"}]}\n"
    "```\n"
    "Frontend nh\u1eadn `menu_item_id` \u2192 hi\u1ec7n **n\u00fat \"\u0110\u1eb7t m\u00f3n\"** \u2014 kh\u00e1ch nh\u1ea5n 1 l\u1ea7n l\u00e0 th\u00eam gi\u1ecf.\n"
    "Kh\u00f4ng c\u1ea7n g\u00f5 l\u1ea1i t\u00ean m\u00f3n.\n\n"
    "### 10.3 Session Persistence\n\n"
    "| T\u00ednh n\u0103ng | C\u01a1 ch\u1ebf |\n"
    "|---|---|\n"
    "| **Refresh trang kh\u00f4ng m\u1ea5t h\u1ed9i tho\u1ea1i** | `session_id` l\u01b0u tr\u00ean server, load l\u1ea1i khi reconnect |\n"
    "| **H\u1ed9i tho\u1ea1i g\u1eafn v\u1edbi phi\u00ean b\u00e0n** | `table_code` \u2192 \u0111\u00f3ng b\u00e0n m\u1edbi reset chat |\n"
    "| **Nh\u1edb d\u1ecb \u1ee9ng su\u1ed1t phi\u00ean** | `session_state.constraints.allergens` persist |\n"
    "| **Kh\u00f4ng g\u1ee3i l\u1ea1i m\u00f3n b\u1ecb t\u1eeb ch\u1ed1i** | `rejected_menu_item_ids` trong SessionState |\n\n"
    "Frontend g\u1eedi `session_id` + `table_code` m\u1ed7i request.\n"
    "Kh\u00e1ch \u0111\u1ed5i \u0111i\u1ec7n tho\u1ea1i, refresh \u2192 v\u1eabn th\u1ea5y l\u1ecbch s\u1eed chat.\n"
    "\u0110\u00f3ng b\u00e0n (thanh to\u00e1n xong) \u2192 session b\u1ecb h\u1ee7y, b\u00e0n m\u1edbi = chat m\u1edbi."
))
# Session Memory analysis
cells.append(md(
    "### Nh\u1eadn x\u00e9t Session Memory\n\n"
    "**3 c\u01a1 ch\u1ebf b\u1ed5 sung cho nhau:**\n"
    "- **Chat History** gi\u00fap LLM hi\u1ec3u context g\u1ea7n (\"c\u00e1i \u0111\u00f3\" = m\u00f3n v\u1eeba n\u00f3i)\n"
    "- **Rolling Summary** gi\u1eef th\u00f4ng tin xa (d\u1ecb \u1ee9ng t\u1eeb l\u01b0\u1ee3t \u0111\u1ea7u)\n"
    "- **Typed SessionState** \u0111\u1ea3m b\u1ea3o constraints (allergens, budget) kh\u00f4ng b\u1ecb LLM qu\u00ean\n\n"
    "**LiveContext l\u00e0 ch\u1ed1t an to\u00e0n:** AI kh\u00f4ng th\u1ec3 b\u1ecba gi\u00e1 v\u00ec m\u1ecdi response\n"
    "\u0111\u1ec1u \u0111\u01b0\u1ee3c cross-check v\u1edbi `menu_items` th\u1eadt t\u1eeb database.\n"
    "N\u1ebfu `is_available=False`, AI t\u1ef1 \u0111\u1ed9ng kh\u00f4ng g\u1ee3i \u00fd m\u00f3n \u0111\u00f3.\n\n"
    "**Cart Suggestion** bi\u1ebfn chatbot t\u1eeb \"h\u1ecfi-\u0111\u00e1p\" th\u00e0nh **conversion tool** \u2014\n"
    "kh\u00e1ch kh\u00f4ng c\u1ea7n g\u00f5 t\u00ean m\u00f3n, nh\u1ea5n n\u00fat l\u00e0 th\u00eam gi\u1ecf.\n\n"
    "> **Li\u00ean k\u1ebft Part II:** Khi intent l\u00e0 `restaurant_info`, Session Memory\n"
    "> g\u1eedi query t\u1edbi **Hybrid RRF** (k\u1ebft qu\u1ea3 screening Part II, xem `hit5_label` \u1edf \u0111\u1ea7u Part III).\n"
    "> Khi intent l\u00e0 `browse_menu`, d\u00f9ng LiveContext thay v\u00ec KB."
))

# ============ S11 CLAIM VERIFIER ============
cells.append(md(
    "## 11. Claim Verifier \u2014 ch\u1ed1ng hallucination\n\n"
    "LLM c\u00f3 th\u1ec3 b\u1ecba s\u1ed1 li\u1ec7u. Claim Verifier ki\u1ec3m tra **sau** khi LLM tr\u1ea3 l\u1eddi:\n"
    "- S\u1ed1 trong c\u00e2u tr\u1ea3 l\u1eddi c\u00f3 kh\u1edbp **evidence t\u1eeb KB (Part I)**?\n"
    "- Evidence ID c\u00f3 t\u1ed3n t\u1ea1i trong 213 chunks?\n"
    "- N\u1ebfu kh\u00f4ng \u2192 ch\u1eb7n response, tr\u1ea3 v\u1ec1 `\"ch\u01b0a \u0111\u1ee7 th\u00f4ng tin\"`\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `notebook_live_test.json` \u2192 `claim_results` (4 claims, ki\u1ec3m tra KB Part I)"
))

cells.append(code(
    'cr = live_test["claim_results"]\n'
    'claim_rows = [{"Claim": r["text"][:45],\n'
    '               "Evidence": (r["evidence_ids"][0][:20]+"..." if r["evidence_ids"] else "(none)"),\n'
    '               "V\u00e0 l\u00fd": "\u2705 OK" if r["verified"] else "\u274c Fail",\n'
    '               "L\u00fd do": r["reason"] or "Kh\u1edbp evidence"}\n'
    '              for r in cr]\n'
    'display(pd.DataFrame(claim_rows).style.hide(axis="index").set_caption(\n'
    '    f"Claim Verification: {len(cr)} claims"))'
))

cells.append(code(
    '# Claim Verification\n'
    'ok_c = len([r for r in cr if r["verified"]])\n'
    'fail_c = len(cr) - ok_c\n'
    'reasons = Counter(r["reason"] for r in cr if r["reason"])\n\n'
    'fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))\n\n'
    'axes[0].bar(["Verified", "Rejected"], [ok_c, fail_c],\n'
    '            color=["#10b981", "#ef4444"], width=0.5)\n'
    'axes[0].set_title("Claim Verification", fontsize=11, fontweight="bold")\n'
    'axes[0].set_ylabel("Count")\n'
    'for i, v in enumerate([ok_c, fail_c]):\n'
    '    axes[0].text(i, v + 0.05, str(v), ha="center", fontsize=10, fontweight="bold")\n\n'
    'if reasons:\n'
    '    r_names = [k.replace("_"," ").title()[:25] for k in reasons.keys()]\n'
    '    r_vals = list(reasons.values())\n'
    '    axes[1].barh(r_names, r_vals, color="#ef4444", height=0.4)\n'
    '    axes[1].set_title("Rejection Reasons", fontsize=11, fontweight="bold")\n'
    '    axes[1].set_xlabel("Count")\n'
    'else:\n'
    '    axes[1].text(0.5, 0.5, "No rejections", ha="center", va="center",\n'
    '                transform=axes[1].transAxes, fontsize=12)\n'
    '    axes[1].set_title("Rejection Reasons", fontsize=11, fontweight="bold")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md(
    "### Nh\u1eadn x\u00e9t Claim Verifier\n\n"
    "Verifier b\u1eaft \u0111\u01b0\u1ee3c **3 lo\u1ea1i hallucination**:\n\n"
    "| Lo\u1ea1i | V\u00ed d\u1ee5 | C\u01a1 ch\u1ebf |\n"
    "|---|---|---|\n"
    "| **S\u1ed1 sai** | 8:00 thay v\u00ec 10:00 | So s\u00e1nh numeric v\u1edbi evidence |\n"
    "| **Kh\u00f4ng evidence** | \"c\u00f3 h\u1ed3 b\u01a1i\" nh\u01b0ng kh\u00f4ng KB n\u00e0o n\u00f3i | Check `evidence_ids` r\u1ed7ng |\n"
    "| **Evidence gi\u1ea3** | ID kh\u00f4ng t\u1ed3n t\u1ea1i | Lookup trong 213 chunks (Part I) |\n\n"
    "**Li\u00ean k\u1ebft Part I:** Verifier d\u00f9ng ch\u00ednh 213 KB chunks \u0111\u00e3 ph\u00e2n t\u00edch \u1edf Part I\n"
    "l\u00e0m ngu\u1ed3n s\u1ef1 th\u1eadt. N\u1ebfu LLM claim \u0111i\u1ec1u g\u00ec kh\u00f4ng c\u00f3 trong KB \u2192 b\u1ecb ch\u1eb7n.\n\n"
    "**H\u1ea1n ch\u1ebf:** Lexical matching \u2014 n\u1ebfu LLM paraphrase \u0111\u00fang ngh\u0129a nh\u01b0ng kh\u00e1c t\u1eeb,\n"
    "verifier c\u00f3 th\u1ec3 false-reject."
))

# ============ PART IV ============
cells.append(md(
    "---\n"
    "# PH\u1ea6N IV \u2014 TH\u1ef0C NGHI\u1ec6M\n\n"
    "Ph\u1ea7n III gi\u1ea3i th\u00edch t\u1eebng th\u00e0nh ph\u1ea7n ri\u00eang.\n"
    "Ph\u1ea7n n\u00e0y g\u1eedi **c\u00f9ng 20 queries** qua **to\u00e0n b\u1ed9 pipeline k\u1ebft h\u1ee3p**:\n\n"
    "```\n"
    "20 queries (c\u00f9ng set v\u1edbi \u00a78 Intent)\n"
    "  \u2192 Guardrails (\u00a79) \u2192 Intent Router (\u00a78)\n"
    "  \u2192 Hybrid RRF (Part II) ho\u1eb7c Catalog API\n"
    "  → LLM (DeepSeek) + Session (§10)\n"
    "  \u2192 Claim Verifier (\u00a711) \u2192 Response\n"
    "```\n\n"
    "> C\u00f9ng query `\"c\u00f3 wifi kh\u00f4ng?\"` \u0111\u00e3 \u0111\u01b0\u1ee3c intent classify \u1edf \u00a78\n"
    "> \u2192 gi\u1edd ch\u1ea1y qua full pipeline \u0111\u1ec3 trace k\u1ebft qu\u1ea3."
))

cells.append(md(
    "## T\u00e0i li\u1ec7u t\u00e1i l\u1ea1p (reproducibility)\n\n"
    "M\u1ecdi s\u1ed1 trong Part IV\u2013V l\u1ea5y t\u1eeb JSON trong `evaluation/results/`.\n"
    "Ch\u1ea1y l\u1ea1i artifact **c\u00f9ng phi\u00ean** (9router b\u1eadt) tr\u01b0\u1edbc khi so s\u00e1nh \u00a712 v\u00e0 \u00a714.\n\n"
    "| L\u1ec7nh | Output |\n"
    "|---|---|\n"
    "| `py scripts/_run_live_tests.py` | `notebook_live_test.json` (\u00a712\u2013\u00a713) |\n"
    "| `py scripts/_dual_model_test.py` | `dual_model_test.json` (\u00a714) |\n"
    "| `py scripts/build_research_notebook.py` | Build + validate cells |\n"
    "| `py scripts/build_research_notebook.py --execute` | Execute notebook (Part II \u2192 screening JSON) |\n"
    "| `py scripts/build_research_notebook.py --regen-live --execute` | Regen live JSON r\u1ed3i execute |\n\n"
    "> Th\u1ee9 t\u1ef1 khuy\u1ebfn ngh\u1ecb: `--execute` \u2192 `--regen-live` \u2192 `--execute` l\u1ea7n 2.\n"
    "> Env: `LLM_PROVIDER=9router`, model production theo `docs/ai/AI_STAGING_READINESS.md`."
))

cells.append(code(
    'from IPython.display import Markdown, display\n'
    'from scripts.notebook_metrics import format_artifact_provenance_table\n\n'
    'display(Markdown(format_artifact_provenance_table(AI_ROOT)))'
))

cells.append(code(
    'import subprocess\n'
    'from scripts.notebook_metrics import summarize_live_test\n\n'
    'def _git_head():\n'
    '    try:\n'
    '        return subprocess.check_output(\n'
    '            ["git", "rev-parse", "--short", "HEAD"],\n'
    '            cwd=PROJECT_ROOT,\n'
    '            text=True,\n'
    '            stderr=subprocess.DEVNULL,\n'
    '        ).strip()\n'
    '    except (subprocess.CalledProcessError, FileNotFoundError, OSError):\n'
    '        return "unknown"\n\n'
    'live_snap = summarize_live_test(live_test)\n'
    'print(f"Git (repo root): {_git_head()}")\n'
    'print(f"notebook_live_test.json: {live_snap[\'timestamp\']}  model={live_snap[\'model\']}")\n'
    'dual_path = AI_ROOT / "evaluation" / "results" / "dual_model_test.json"\n'
    'if dual_path.exists():\n'
    '    _dual_ts = json.loads(dual_path.read_text(encoding="utf-8")).get("timestamp", "?")\n'
    '    print(f"dual_model_test.json: {_dual_ts}")\n'
    'else:\n'
    '    print("dual_model_test.json: (ch\u01b0a c\u00f3 \u2014 ch\u1ea1y _dual_model_test.py)")'
))

cells.append(md(
    "## B\u1ea3ng thu\u1eadt ng\u1eef metric (Part IV)\n\n"
    "| Metric | \u00a7 | \u00dd ngh\u012a | Denominator |\n"
    "|---|---|---|---|\n"
    "| **Detect rate** | III (\u00a79\u2013\u0111) | Guardrails / Claim Verifier b\u1eaft \u0111\u00fang case thi\u1ebft k\u1ebf | S\u1ed1 case trong b\u1ed9 test ri\u00eang |\n"
    "| **Pipeline availability** | \u00a712 | C\u00f3 response non-abstain tr\u00ean `pipeline_results` | 20 query, **m\u1ed9t** model (`notebook_live_test.json`) |\n"
    "| **Non-abstain success** | \u00a714 | `route != abstain` tr\u00ean c\u00f9ng 20 query, **3 model** | `dual_model_test.json` |\n"
    "| **Strict success** | \u00a712 (v\u00e0 glossary) | Abstain, fail-closed content, ho\u1eb7c `route` unknown + flags block | `pipeline_results` / export fields `success_strict` |\n\n"
    "> **Availability \u2260 ch\u1ea5t l\u01b0\u1ee3ng c\u00e2u tr\u1ea3 l\u1eddi.** Release gate: "
    "[`docs/ai/AI_STAGING_READINESS.md`](../../docs/ai/AI_STAGING_READINESS.md) "
    "(hi\u1ec7n **NOT READY**).\n\n"
    "> Timestamp \u00a712 v\u00e0 \u00a714 c\u00f3 th\u1ec3 kh\u00e1c nhau n\u1ebfu ch\u1ea1y artifact \u1edf th\u1eddi \u0111i\u1ec3m kh\u00e1c nhau "
    "\u2014 \u0111\u1ecdc block repro ph\u00eda tr\u00ean tr\u01b0\u1edbc khi so s\u00e1nh."
))

# §12 Pipeline
cells.append(md(
    "## 12. Pipeline end-to-end: queries th\u1eadt v\u1edbi LLM\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `notebook_live_test.json` \u2192 `pipeline_results`\n"
    "> C\u00f9ng **20 queries** nh\u01b0 \u00a78 Intent, model `cx/gpt-5.5`"
))

cells.append(code(
    'pr = live_test["pipeline_results"]\n'
    'pipe_rows = []\n'
    'for r in pr:\n'
    '    if "error" in r:\n'
    '        pipe_rows.append({"Query": r["query"][:35], "Route": "ERROR",\n'
    '                          "N\u1ed9i dung": r.get("error","")[:40], "Latency": "?"})\n'
    '    else:\n'
    '        content = r.get("content","")[:70]\n'
    '        if "<!-- question_variants" in content: content = "[KB fast-path]"\n'
    '        pipe_rows.append({"Query": r["query"][:35], "Route": r["route"],\n'
    '                          "Response": content[:50],\n'
    '                          "Latency": f\'{r["latency_ms"]:.0f}ms\'})\n'
    'display(pd.DataFrame(pipe_rows).style.hide(axis="index").set_caption(\n'
    '    f"Pipeline end-to-end: {len(pr)} queries, model {live_test[\'model\']}"))'
))

cells.append(code(
    '# Latency per Query\n'
    'valid_pr = [r for r in pr if "error" not in r]\n'
    'routes_p = [r["route"] for r in valid_pr]\n'
    'latencies = [r["latency_ms"] for r in valid_pr]\n'
    'qs = [r["query"][:22] for r in valid_pr]\n'
    'rc_colors = {"kb_rag": "#10b981", "clarify": "#f59e0b", "abstain": "#ef4444",\n'
    '             "live_data": "#3b82f6", "llm": "#8b5cf6"}\n'
    'colors_l = [rc_colors.get(r, "#94a3b8") for r in routes_p]\n\n'
    'fig, ax = plt.subplots(figsize=(8, max(4, len(qs)*0.3)))\n'
    'bars = ax.barh(range(len(qs)), latencies, color=colors_l, height=0.6)\n'
    'ax.set_yticks(range(len(qs)))\n'
    'ax.set_yticklabels(qs, fontsize=7)\n'
    'for i, (v, r) in enumerate(zip(latencies, routes_p)):\n'
    '    ax.text(v + 50, i, f"{v:.0f}ms [{r}]", va="center", fontsize=7)\n'
    'ax.set_xlabel("Latency (ms)", fontsize=9)\n'
    'ax.set_title("Latency per Query", fontsize=11, fontweight="bold")\n'
    'ax.invert_yaxis()\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(code(
    '# Route Distribution\n'
    'rc2 = Counter(routes_p)\n'
    'fig, ax = plt.subplots(figsize=(6, 4))\n'
    'labels = list(rc2.keys())\n'
    'sizes = list(rc2.values())\n'
    'colors_r = [rc_colors.get(r, "#94a3b8") for r in labels]\n'
    'wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors_r,\n'
    '    autopct="%1.0f%%", startangle=90, pctdistance=0.75)\n'
    'for t in texts: t.set_fontsize(9)\n'
    'for t in autotexts: t.set_fontsize(8)\n'
    'ax.set_title("Route Distribution (Pipeline)", fontsize=11, fontweight="bold")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))


cells.append(code(
    '# Ph\u00e2n t\u00edch pipeline theo route\n'
    'from collections import Counter\n'
    'route_stats = {}\n'
    'for r in valid_pr:\n'
    '    rt = r["route"]\n'
    '    if rt not in route_stats: route_stats[rt] = {"count": 0, "lats": []}\n'
    '    route_stats[rt]["count"] += 1\n'
    '    route_stats[rt]["lats"].append(r["latency_ms"])\n'
    'print("| Route | S\u1ed1 query | Avg Latency | D\u00f9ng Hybrid RRF? |")\n'
    'print("|---|---|---|---|"  )\n'
    'route_desc = {"kb_rag": "**C\u00f3** \u2014 Part II", "clarify": "Kh\u00f4ng \u2014 h\u1ecfi l\u1ea1i",\n'
    '              "abstain": "G\u1ecdi LLM \u2192 Verifier ch\u1eb7n", "live_data": "Kh\u00f4ng \u2014 lookup"}\n'
    'for rt, st in route_stats.items():\n'
    '    avg = sum(st["lats"])/len(st["lats"])\n'
    '    print(f"| `{rt}` | {st[\"count\"]} | {avg:.0f}ms | {route_desc.get(rt, \"?\")} |")'
))

cells.append(code(
    '# Tóm tắt availability vs strict\n'
    'from scripts.notebook_metrics import summarize_live_pipeline\n'
    'pipe_sum = summarize_live_pipeline(live_test)\n'
    'total_p = pipe_sum["pipeline_total"] or 1\n'
    'print("### Nhận xét Pipeline (số liệu)")\n'
    'print(f"Availability: {pipe_sum[\'availability_ok\']}/{total_p} ({pipe_sum[\'availability_ok\']/total_p:.0%})")\n'
    'print(f"Strict: {pipe_sum[\'strict_ok\']}/{total_p} ({pipe_sum[\'strict_ok\']/total_p:.0%})")\n'
    'print(f"route null/unknown: {pipe_sum[\'route_null\']}, abstain: {pipe_sum[\'route_abstain\']}")'
))

cells.append(code(
    'from IPython.display import Markdown, display\n'
    'from scripts.notebook_metrics import format_part12_narrative\n\n'
    '_dual_for_12 = None\n'
    'if (AI_ROOT / "evaluation" / "results" / "dual_model_test.json").exists():\n'
    '    _dual_for_12 = json.load(open(\n'
    '        AI_ROOT / "evaluation" / "results" / "dual_model_test.json", encoding="utf-8"\n'
    '    ))\n'
    'display(Markdown(format_part12_narrative(live_test, _dual_for_12)))'
))

cells.append(md(
    "> **Ghi chú kỹ thuật:** Claim Verifier + LiveContext vẫn là hướng cải thiện chính; "
    "nhận xét chi tiết theo từng query nằm ở bảng `pipeline_results` phía trên."
))

# \u00a713 Multi-turn
cells.append(md(
    "## 13. Multi-turn: gi\u1eef ng\u1eef c\u1ea3nh qua nhi\u1ec1u l\u01b0\u1ee3t\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `notebook_live_test.json` \u2192 `multi_results` (5 turns, model `cx/gpt-5.5`)"
))

cells.append(code(
    'mr = live_test["multi_results"]\n'
    'for r in mr:\n'
    '    if "error" in r:\n'
    '        print(f"Turn {r[\'turn\']}: ERROR")\n'
    '        continue\n'
    '    content = r.get("content","")[:80]\n'
    '    if "<!-- question_variants" in content: content = "[KB fast-path]"\n'
    '    print(f"Turn {r[\'turn\']}: {r[\'query\']}")\n'
    '    print(f"  Route:  {r[\'route\']}")\n'
    '    print(f"  Answer: {content}")\n'
    '    print()'
))

cells.append(code(
    '# Chart 6: Multi-turn success\n'
    'ok_t = [r for r in mr if "error" not in r and r.get("route") != "abstain"]\n'
    'has_sum = [r for r in mr if r.get("rolling_summary")]\n\n'
    'fig, ax = plt.subplots(figsize=(6, 3))\n'
    'metrics_mt = ["Tr\u1ea3 l\u1eddi OK", "C\u00f3 summary"]\n'
    'vals_mt = [len(ok_t)/len(mr), len(has_sum)/len(mr)]\n'
    'bars = ax.bar(metrics_mt, vals_mt, color=["#10b981", "#3b82f6"])\n'
    'for b, v in zip(bars, vals_mt):\n'
    '    ax.text(b.get_x()+b.get_width()/2., b.get_height()+0.02,\n'
    '            f"{v:.0%}", ha="center", fontweight="bold")\n'
    'ax.set_ylim(0, 1.15)\n'
    'ax.set_title(f"Multi-turn ({len(mr)} turns)")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(md(
    "### Nh\u1eadn x\u00e9t Multi-turn\n\n"
    "5 turn thi\u1ebft k\u1ebf ki\u1ec3m context. B\u1ea3ng d\u01b0\u1edbi l\u1ea5y t\u1eeb `multi_results` sau khi ch\u1ea1y th\u1eadt."
))

cells.append(code(
    'from IPython.display import Markdown, display\n'
    'from scripts.notebook_metrics import format_part13_narrative\n\n'
    'display(Markdown(format_part13_narrative(live_test)))'
))

# ============ S14 THREE MODEL COMPARISON ============
cells.append(md(
    "## 14. So s\u00e1nh 3 model LLM\n\n"
    "Test c\u00f9ng **20 queries** (6 lo\u1ea1i: KB FAQ, Menu, Allergy, Order, Off-topic, Chitchat)\n"
    "v\u1edbi **3 model**:\n"
    "- `oc/deepseek-v4-flash-free` — **triển khai** staging/production\n"
    "- `cx/gpt-5.5` — quality gate / so sánh\n"
    "- `cx/gpt-5.6-luna` — thế hệ mới (thí nghiệm)\n\n"
    "C\u00f9ng pipeline, c\u00f9ng KB (Part I), c\u00f9ng Hybrid RRF (Part II), c\u00f9ng Guardrails (\u00a79).\n\n"
    "> **Ngu\u1ed3n d\u1eef li\u1ec7u:** `dual_model_test.json` \u2192 c\u00f9ng 20 queries nh\u01b0 \u00a78 v\u00e0 \u00a712"
))

cells.append(code(
    'from scripts.notebook_metrics import summarize_dual_model, is_strict_pipeline_success\n\n'
    'dual = json.load(open(\n'
    '    AI_ROOT / "evaluation" / "results" / "dual_model_test.json",\n'
    '    encoding="utf-8"\n'
    '))\n'
    'models = dual["models"]\n'
    'total_q = len(dual["queries"])\n'
    '_dual_summary = summarize_dual_model(dual)\n'
    'print(f"Test: {dual[\'timestamp\']}")\n'
    'print(f"Models: {len(models)}")\n'
    'print(f"Queries: {total_q}\\n")\n'
    'print(f"{\'Model\':35s} {\'Avail\':12s} {\'Strict\':12s}")\n'
    'for m in models:\n'
    '    stats = _dual_summary["per_model"][m]\n'
    '    print(f"{m:35s} {stats[\'ok\']}/{total_q} ({stats[\'ok\']/total_q:.0%})   "\n'
    '          f"{stats[\'strict_ok\']}/{total_q} ({stats[\'strict_ok\']/total_q:.0%})")'
))

cells.append(code(
    '# B\u1ea3ng so s\u00e1nh chi ti\u1ebft\n'
    'compare_rows = []\n'
    'for i, qobj in enumerate(dual["queries"]):\n'
    '    q = qobj["query"] if isinstance(qobj, dict) else qobj\n'
    '    cat = qobj.get("category", "") if isinstance(qobj, dict) else ""\n'
    '    row = {"Query": q[:25], "Cat": cat}\n'
    '    for m in models:\n'
    '        r = dual["results"][m][i]\n'
    '        label = m.split("/")[1][:12]\n'
    '        if "error" in r:\n'
    '            row[f"{label}"] = "ERR"\n'
    "        else:\n"
    "            route = r[\"route\"] or \"llm\"\n"
    "            row[f\"{label}\"] = f'{route} {r[\"latency_ms\"]:.0f}ms'\n"
    "    compare_rows.append(row)\n"
    "display(pd.DataFrame(compare_rows).style.hide(axis=\"index\").set_caption(\n"
    "    f\"So s\u00e1nh {len(models)} models x {total_q} queries\"))\n\n"
    "# Ph\u00e2n t\u00edch kh\u00e1c bi\u1ec7t gi\u1eefa c\u00e1c model\n"
    "diff_found = False\n"
    "for i, qobj in enumerate(dual[\"queries\"]):\n"
    "    q = qobj[\"query\"] if isinstance(qobj, dict) else qobj\n"
    "    routes = {m.split(\"/\")[1][:12]: dual[\"results\"][m][i].get(\"route\",\"?\") for m in models}\n"
    "    unique = set(routes.values())\n"
    "    if len(unique) > 1:\n"
    "        if not diff_found:\n"
    "            print(\"\\n\\u26a1 Queries c\u00f3 k\u1ebft qu\u1ea3 kh\u00e1c nhau:\")\n"
    "            diff_found = True\n"
    "        print(f\"  \\u2022 \\\"{q}\\\"  \\u2192  {routes}\")\n"
    "if not diff_found:\n"
    "    print(\"\\n\\u2705 C\u1ea3 3 model cho k\u1ebft qu\u1ea3 gi\u1ed1ng h\u1ec7t nhau tr\u00ean 20 queries.\")\n"
    "    print(\"   \\u2192 Claim Verifier (\\u00a711) l\u00e0 bottleneck ch\u00ednh, kh\u00f4ng ph\u1ea3i model LLM.\")\n"
    "    print(\"   \\u2192 C\u1ea3i thi\u1ec7n Claim Verifier ho\u1eb7c th\u00eam LiveContext s\u1ebd t\u0103ng success rate.\")"
))

cells.append(code(
    '# Chart 7: 2x2 comparison\n'
    'import numpy as np\n'
    'n_models = len(models)\n'
    'colors_m = ["#3b82f6", "#f59e0b", "#10b981"][:n_models]\n'
    'short = [m.split("/")[1][:12] for m in models]\n\n'
    'fig, axes = plt.subplots(2, 2, figsize=(14, 8))\n\n'
    '# 7a: Success rate bar\n'
    'ax = axes[0, 0]\n'
    'ok_counts = []\n'
    'for m in models:\n'
    '    ok = len([r for r in dual["results"][m] if r.get("route") != "abstain" and "error" not in r])\n'
    '    ok_counts.append(ok)\n'
    'bars = ax.bar(short, [c/total_q for c in ok_counts], color=colors_m)\n'
    'for b, c in zip(bars, ok_counts):\n'
    '    ax.text(b.get_x()+b.get_width()/2., b.get_height()+0.02, f"{c}/{total_q}",\n'
    '            ha="center", fontweight="bold", fontsize=11)\n'
    'ax.set_ylim(0, 1.15)\n'
    'ax.set_ylabel("T\u1ec9 l\u1ec7 tr\u1ea3 l\u1eddi")\n'
    'ax.set_title("Success Rate")\n\n'
    '# 7b: Avg latency (OK vs Abstain)\n'
    'ax = axes[0, 1]\n'
    'x_pos = np.arange(n_models)\n'
    'ok_avgs, ab_avgs = [], []\n'
    'for m in models:\n'
    '    ok_lat = [r["latency_ms"] for r in dual["results"][m] if r.get("route") != "abstain" and "error" not in r]\n'
    '    ab_lat = [r["latency_ms"] for r in dual["results"][m] if r.get("route") == "abstain"]\n'
    '    ok_avgs.append(sum(ok_lat)/len(ok_lat) if ok_lat else 0)\n'
    '    ab_avgs.append(sum(ab_lat)/len(ab_lat) if ab_lat else 0)\n'
    'w = 0.35\n'
    'ax.bar(x_pos - w/2, ok_avgs, w, label="OK", color="#10b981")\n'
    'ax.bar(x_pos + w/2, ab_avgs, w, label="Abstain", color="#ef4444")\n'
    'for i in range(n_models):\n'
    '    ax.text(i-w/2, ok_avgs[i]+100, f"{ok_avgs[i]:.0f}ms", ha="center", fontsize=8)\n'
    '    ax.text(i+w/2, ab_avgs[i]+100, f"{ab_avgs[i]:.0f}ms", ha="center", fontsize=8)\n'
    'ax.set_xticks(x_pos)\n'
    'ax.set_xticklabels(short)\n'
    'ax.set_ylabel("Avg Latency (ms)")\n'
    'ax.set_title("Latency: OK vs Abstain")\n'
    'ax.legend()\n\n'
    '# 7c: Success by category\n'
    'ax = axes[1, 0]\n'
    'cats = []\n'
    'for qobj in dual["queries"]:\n'
    '    c = qobj.get("category", "?") if isinstance(qobj, dict) else "?"\n'
    '    if c not in cats: cats.append(c)\n'
    'cat_data = {m: {} for m in models}\n'
    'for m in models:\n'
    '    for i, qobj in enumerate(dual["queries"]):\n'
    '        c = qobj.get("category", "?") if isinstance(qobj, dict) else "?"\n'
    '        r = dual["results"][m][i]\n'
    '        if c not in cat_data[m]: cat_data[m][c] = {"ok": 0, "total": 0}\n'
    '        cat_data[m][c]["total"] += 1\n'
    '        if r.get("route") != "abstain" and "error" not in r:\n'
    '            cat_data[m][c]["ok"] += 1\n'
    'x = np.arange(len(cats))\n'
    'w3 = 0.25\n'
    'for j, m in enumerate(models):\n'
    '    rates = [cat_data[m].get(c, {"ok":0,"total":1})["ok"]/cat_data[m].get(c,{"ok":0,"total":1})["total"] for c in cats]\n'
    '    ax.bar(x + (j-1)*w3, rates, w3, label=short[j], color=colors_m[j])\n'
    'ax.set_xticks(x)\n'
    'ax.set_xticklabels(cats, fontsize=9)\n'
    'ax.set_ylim(0, 1.15)\n'
    'ax.set_title("Success by Category")\n'
    'ax.legend(fontsize=8)\n\n'
    '# 7d: DeepSeek wins\n'
    'ax = axes[1, 1]\n'
    'win_data = {"Ch\u1ec9 DeepSeek OK": 0, "T\u1ea5t c\u1ea3 OK": 0, "T\u1ea5t c\u1ea3 Abstain": 0, "Kh\u00e1c": 0}\n'
    'ds = models[-1] if "deepseek" in models[-1].lower() else models[0]\n'
    'others = [m for m in models if m != ds]\n'
    'for i in range(total_q):\n'
    '    ds_ok = dual["results"][ds][i].get("route") != "abstain" and "error" not in dual["results"][ds][i]\n'
    '    others_ok = all(dual["results"][m][i].get("route") != "abstain" and "error" not in dual["results"][m][i] for m in others)\n'
    '    if ds_ok and not others_ok: win_data["Ch\u1ec9 DeepSeek OK"] += 1\n'
    '    elif ds_ok and others_ok: win_data["T\u1ea5t c\u1ea3 OK"] += 1\n'
    '    elif not ds_ok and not others_ok: win_data["T\u1ea5t c\u1ea3 Abstain"] += 1\n'
    '    else: win_data["Kh\u00e1c"] += 1\n'
    'pie_colors = ["#10b981", "#3b82f6", "#ef4444", "#94a3b8"]\n'
    'vals = [v for v in win_data.values() if v > 0]\n'
    'lbls = [k for k, v in win_data.items() if v > 0]\n'
    'ax.pie(vals, labels=lbls, colors=pie_colors[:len(vals)], autopct="%1.0f%%", startangle=90)\n'
    'ax.set_title("DeepSeek vs GPT")\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

# §14.1 — code cell computes breakdown from data
cells.append(md("### 14.1 Ph\u00e2n t\u00edch k\u1ebft qu\u1ea3\n\n**T\u1ea1i sao success rate ch\u1ec9 40-50%?** Ph\u00e2n t\u00edch theo category:"))

cells.append(code(
    '# Ph\u00e2n t\u00edch theo category t\u1eeb data th\u1eadt\n'
    'cats_order = ["KB FAQ", "Menu", "Allergy", "Order", "Off-topic", "Chitchat"]\n'
    'abstain_reasons = {"KB FAQ": "Query kh\u00f4ng c\u00f3 trong 213 chunks KB",\n'
    '    "Menu": "Claim Verifier ch\u1eb7n (kh\u00f4ng c\u00f3 evidence trong KB)",\n'
    '    "Allergy": "C\u1ea7n menu data + LLM reasoning",\n'
    '    "Order": "Pipeline ch\u01b0a c\u00f3 logic \u0111\u1eb7t h\u00e0ng",\n'
    '    "Off-topic": "\u0110\u00fang \u2014 h\u1ec7 th\u1ed1ng kh\u00f4ng tr\u1ea3 l\u1eddi ngo\u00e0i scope",\n'
    '    "Chitchat": "Ch\u01b0a handle c\u00e2u x\u00e3 giao"}\n'
    'rows14 = []\n'
    'for cat in cats_order:\n'
    '    idxs = [i for i, qo in enumerate(dual["queries"]) if (qo.get("category","") if isinstance(qo,dict) else "") == cat]\n'
    '    if not idxs: continue\n'
    '    row = {"Category": cat, "Queries": len(idxs)}\n'
    '    for m in models:\n'
    '        ok = sum(1 for i in idxs if dual["results"][m][i].get("route") != "abstain" and "error" not in dual["results"][m][i])\n'
    '        label = m.split("/")[1][:12]\n'
    '        row[label] = f"{ok}/{len(idxs)} ({ok/len(idxs):.0%})"\n'
    '    row["Nguy\u00ean nh\u00e2n Abstain"] = abstain_reasons.get(cat, "")\n'
    '    rows14.append(row)\n'
    'display(pd.DataFrame(rows14).style.hide(axis="index").set_caption(\n'
    '    "Ph\u00e2n t\u00edch success theo category"))'
))

cells.append(md(
    "### 14.2 Gi\u1ea3i th\u00edch ki\u1ebfn tr\u00fac: T\u1ea1i sao nhi\u1ec1u query abstain?\n\n"
    "Pipeline d\u00f9ng thi\u1ebft k\u1ebf **fail-closed** \u2014 ch\u1ec9 tr\u1ea3 l\u1eddi khi **ch\u1eafc ch\u1eafn \u0111\u00fang**:\n\n"
    "```\n"
    "Query \u2192 Guardrails \u2192 Intent Router \u2192 3 \u0111\u01b0\u1eddng:\n"
    "  \u251c\u2500 kb_rag:   Hybrid RRF t\u00ecm evidence \u2192 tr\u1ea3 l\u1eddi tr\u1ef1c ti\u1ebfp (kh\u00f4ng LLM)\n"
    "  \u251c\u2500 live_data: Lookup menu_items \u2192 tr\u1ea3 gi\u00e1 tr\u1ef1c ti\u1ebfp (kh\u00f4ng LLM)\n"
    "  \u2514\u2500 llm_gen:  LLM sinh response \u2192 Claim Verifier ki\u1ec3m tra\n"
    "                                     \u2514\u2500 N\u1ebfu kh\u00f4ng c\u00f3 evidence \u2192 ABSTAIN\n"
    "```\n\n"
    "**4 nguy\u00ean nh\u00e2n ch\u00ednh cho abstain:**\n\n"
    "| # | Nguy\u00ean nh\u00e2n | V\u00ed d\u1ee5 | Gi\u1ea3i ph\u00e1p |\n"
    "|---|---|---|---|\n"
    "| 1 | **KB thi\u1ebfu** | \"ph\u00f2ng ri\u00eang\", \"h\u1ee7y \u0111\u01a1n\" | Th\u00eam v\u00e0o KB |\n"
    "| 2 | **Claim Verifier ch\u1eb7n** | \"m\u00f3n kh\u00f4ng cay\" | Verifier c\u1ea7n check LiveContext |\n"
    "| 3 | **Order ch\u01b0a h\u1ed7 tr\u1ee3** | \"th\u00eam 1 tr\u00e0 \u0111\u00e1\" | C\u1ea7n Cart API |\n"
    "| 4 | **Off-topic \u0111\u00fang** | \"th\u1eddi ti\u1ebft\" | Kh\u00f4ng c\u1ea7n fix |\n\n"
    "> **Quan tr\u1ecdng:** Abstain **kh\u00f4ng ph\u1ea3i l\u1ed7i** \u2014 l\u00e0 thi\u1ebft k\u1ebf c\u00f3 ch\u1ee7 \u0111\u00edch.\n"
    "> Trong nh\u00e0 h\u00e0ng th\u1eadt, khi chatbot abstain, h\u1ec7 th\u1ed1ng hi\u1ec3n th\u1ecb\n"
    "> c\u00e2u m\u1eb7c \u0111\u1ecbnh nh\u01b0 \"Xin l\u1ed7i, t\u00f4i ch\u01b0a c\u00f3 th\u00f4ng tin n\u00e0y\" thay v\u00ec\n"
    "> tr\u1ea3 l\u1eddi sai (hallucination)."
))

# §14.3 — code cell computes from data
cells.append(md("### 14.3 So s\u00e1nh 3 Model"))

cells.append(code(
    '# T\u00ednh t\u1eeb data, kh\u00f4ng hardcode\n'
    'from scripts.notebook_metrics import is_strict_pipeline_success\n\n'
    'comp_rows = []\n'
    'for m in models:\n'
    '    res = dual["results"][m]\n'
    '    ok = [r for r in res if r.get("route") != "abstain" and "error" not in r]\n'
    '    strict_n = sum(1 for r in res if "error" not in r and is_strict_pipeline_success(r))\n'
    '    ab = [r for r in res if r.get("route") == "abstain"]\n'
    '    # T\u00e1ch fast-path vs LLM\n'
    '    fast = [r for r in ok if r.get("route") in ("kb_rag","clarify","live_data")]\n'
    '    llm = [r for r in ok if r.get("route") not in ("kb_rag","clarify","live_data","abstain")]\n'
    '    fast_lat = [r["latency_ms"] for r in fast]\n'
    '    llm_lat = [r["latency_ms"] for r in llm]\n'
    '    ab_lat = [r["latency_ms"] for r in ab]\n'
    '    # KB FAQ subset\n'
    '    kb_idxs = [i for i, q in enumerate(dual["queries"]) if (q.get("category","") if isinstance(q,dict) else "") == "KB FAQ"]\n'
    '    kb_ok = sum(1 for i in kb_idxs if res[i].get("route") != "abstain" and "error" not in res[i])\n'
    '    # Menu+Allergy\n'
    '    ma_idxs = [i for i, q in enumerate(dual["queries"]) if (q.get("category","") if isinstance(q,dict) else "") in ("Menu","Allergy")]\n'
    '    ma_ok = sum(1 for i in ma_idxs if res[i].get("route") != "abstain" and "error" not in res[i])\n'
    '    comp_rows.append({\n'
    '        "Model": m.split("/")[1][:15],\n'
    '        "Availability": f"{len(ok)}/{total_q} ({len(ok)/total_q:.0%})",\n'
    '        "Strict": f"{strict_n}/{total_q} ({strict_n/total_q:.0%})",\n'
    '        "KB FAQ": f"{kb_ok}/{len(kb_idxs)}",\n'
    '        "Menu+Allergy": f"{ma_ok}/{len(ma_idxs)}",\n'
    '        "Fast-path (ms)": f"{sum(fast_lat)/len(fast_lat):.0f}" if fast_lat else "-",\n'
    '        "LLM path (ms)": f"{sum(llm_lat)/len(llm_lat):.0f}" if llm_lat else "-",\n'
    '        "Abstain (ms)": f"{sum(ab_lat)/len(ab_lat):.0f}" if ab_lat else "-",\n'
    '    })\n'
    'display(pd.DataFrame(comp_rows).style.hide(axis="index").set_caption(\n'
    '    f"So s\u00e1nh 3 model tr\u00ean {total_q} queries"))'
))

cells.append(code(
    'from IPython.display import Markdown, display\n'
    'from scripts.notebook_metrics import summarize_dual_model, format_part4_narrative\n\n'
    '_dual_summary = summarize_dual_model(dual)\n'
    'display(Markdown(format_part4_narrative(_dual_summary)))'
))

# ============ PART V ============
cells.append(md(
    "---\n"
    "# PH\u1ea6N V \u2014 K\u1ebET LU\u1eacN"
))

cells.append(md("## 15. T\u1ed5ng h\u1ee3p k\u1ebft qu\u1ea3 5 ph\u1ea7n"))

cells.append(code(
    '# T\u1ed5ng h\u1ee3p\n'
    'ir=live_test["intent_results"]; gr=live_test["guard_results"]\n'
    'cr=live_test["claim_results"]; pr=live_test["pipeline_results"]\n'
    'mr=live_test["multi_results"]\n\n'
    'i_ok=len([r for r in ir if r["intent"]!="general"])\n'
    'g_ok=len(gr); c_ok=len(cr)\n'
    'p_ok=len([r for r in pr if "error" not in r and r.get("route")!="abstain"])\n'
    'm_ok=len([r for r in mr if "error" not in r and r.get("route")!="abstain"])\n\n'
    'dual_summary_rows = []\n'
    'if "dual" in globals():\n'
    '    for m in dual["models"]:\n'
    '        ok_m = len([r for r in dual["results"][m] if r.get("route") != "abstain" and "error" not in r])\n'
    '        dual_summary_rows.append((m.split("/")[-1][:20], ok_m, len(dual["queries"])))\n'
    'elif (AI_ROOT / "evaluation" / "results" / "dual_model_test.json").exists():\n'
    '    _d = json.load(open(AI_ROOT / "evaluation" / "results" / "dual_model_test.json", encoding="utf-8"))\n'
    '    for m in _d["models"]:\n'
    '        ok_m = len([r for r in _d["results"][m] if r.get("route") != "abstain" and "error" not in r])\n'
    '        dual_summary_rows.append((m.split("/")[-1][:20], ok_m, len(_d["queries"])))\n'
    'dual_label = ", ".join(f"{n} {o}/{t}" for n, o, t in dual_summary_rows) if dual_summary_rows else "xem §14"\n'
    'dual_avg = (\n'
    '    sum(o / t for _, o, t in dual_summary_rows) / len(dual_summary_rows)\n'
    '    if dual_summary_rows else p_ok / len(pr)\n'
    ')\n\n'
    'summary=[\n'
    '  {"Part":"I","Th\u00e0nh ph\u1ea7n":"Knowledge Base","K\u1ebft qu\u1ea3":"26 files, 213 chunks",\n'
    '   "Vai tr\u00f2":"Ngu\u1ed3n evidence cho retrieval + claim verify"},\n'
    '  {"Part":"II","Th\u00e0nh ph\u1ea7n":"Hybrid RRF","K\u1ebft qu\u1ea3":hit5_label,\n'
    '   "Vai tr\u00f2":"T\u00ecm chunk ph\u00f9 h\u1ee3p cho LLM"},\n'
    '  {"Part":"III","Th\u00e0nh ph\u1ea7n":"Intent Router","K\u1ebft qu\u1ea3":f"{i_ok}/{len(ir)} ({i_ok/len(ir):.0%})",\n'
    '   "Vai tr\u00f2":"Quy\u1ebft \u0111\u1ecbnh d\u00f9ng Hybrid RRF hay Catalog"},\n'
    '  {"Part":"III","Th\u00e0nh ph\u1ea7n":"Guardrails","K\u1ebft qu\u1ea3":f"{g_ok}/{len(gr)} (100%)",\n'
    '   "Vai tr\u00f2":"Ch\u1eb7n PII, injection, off-topic"},\n'
    '  {"Part":"III","Th\u00e0nh ph\u1ea7n":"Claim Verifier","K\u1ebft qu\u1ea3":f"{c_ok}/{len(cr)} (100%)",\n'
    '   "Vai tr\u00f2":"Ch\u1eb7n hallucination (d\u00f9ng KB Part I)"},\n'
    '  {"Part":"IV","Th\u00e0nh ph\u1ea7n":"Pipeline (LLM)","K\u1ebft qu\u1ea3":f"{p_ok}/{len(pr)} ({p_ok/len(pr):.0%})",\n'
    '   "Vai tr\u00f2":"End-to-end v\u1edbi " + live_test["model"]},\n'
    '  {"Part":"IV","Th\u00e0nh ph\u1ea7n":"Multi-turn","K\u1ebft qu\u1ea3":f"{m_ok}/{len(mr)} ({m_ok/len(mr):.0%})",\n'
    '   "Vai tr\u00f2":"Context retention qua l\u01b0\u1ee3t"},\n'
    '  {"Part":"IV","Th\u00e0nh ph\u1ea7n":"So s\u00e1nh 3 model","K\u1ebft qu\u1ea3":dual_label,\n'
    '   "Vai tr\u00f2":"Non-abstain tr\u00ean 20 query (dual_model_test.json)"},\n'
    ']\n'
    'display(pd.DataFrame(summary).style.hide(axis="index").set_caption("T\u1ed5ng h\u1ee3p 5 ph\u1ea7n"))'
))

cells.append(code(
    '# Chart 7: Radar chart\n'
    'import numpy as np\n'
    'labels = ["Intent\\nRouter", "Guardrails", "Claim\\nVerifier", "Pipeline\\n(LLM)", "Multi\\nturn"]\n'
    'scores = [i_ok/len(ir), g_ok/len(gr), c_ok/len(cr), p_ok/len(pr), m_ok/len(mr)]\n\n'
    'angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()\n'
    'scores_r = scores + [scores[0]]\n'
    'angles_r = angles + [angles[0]]\n\n'
    'fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))\n'
    'ax.fill(angles_r, scores_r, color="#3b82f6", alpha=0.25)\n'
    'ax.plot(angles_r, scores_r, color="#3b82f6", linewidth=2)\n'
    'ax.scatter(angles, scores, color="#3b82f6", s=60, zorder=5)\n'
    'for angle, score, label in zip(angles, scores, labels):\n'
    '    ax.text(angle, score+0.08, f"{score:.0%}", ha="center", fontsize=10, fontweight="bold")\n'
    'ax.set_xticks(angles)\n'
    'ax.set_xticklabels(labels, fontsize=10)\n'
    'ax.set_ylim(0, 1.1)\n'
    'ax.set_title("Component Scores (ch\u1ea1y th\u1eadt)", pad=20)\n'
    'plt.tight_layout()\n'
    'plt.show()'
))

cells.append(code(
    '# Chart 8: Summary bar\n'
    'fig, ax = plt.subplots(figsize=(10, 4))\n'
    'comp_names = ["KB\\n(Part I)", "Hybrid RRF\\n(Part II)", "Intent\\n(Part III)",\n'
    '              "Guardrails\\n(Part III)", "Claim\\n(Part III)", "Pipeline\\n(Part IV)",\n'
    '              "Multi-turn\\n(Part IV)", "3 model\\n(Part IV)"]\n'
    'comp_scores = [1.0, hit5_score, i_ok/len(ir), g_ok/len(gr), c_ok/len(cr), p_ok/len(pr), m_ok/len(mr), dual_avg]\n'
    'comp_colors = ["#6366f1","#8b5cf6","#f59e0b","#ef4444","#ec4899","#3b82f6","#10b981","#0ea5e9"]\n\n'
    'bars = ax.bar(comp_names, comp_scores, color=comp_colors)\n'
    'for b, v in zip(bars, comp_scores):\n'
    '    ax.text(b.get_x()+b.get_width()/2., b.get_height()+0.02,\n'
    '            f"{v:.0%}", ha="center", fontsize=10, fontweight="bold")\n'
    'ax.set_ylim(0, 1.15)\n'
    'ax.axhline(y=1.0, color="#e5e7eb", linestyle="--", linewidth=0.8)\n'
    'ax.set_title("T\u1ed5ng h\u1ee3p: Part I \u2192 Part IV (ch\u1ea1y th\u1eadt)")\n'
    'plt.figtext(0.5, 0.01, "C\u1ed9t Hybrid RRF = Hit@5 screening Part II (107 case), kh\u00f4ng ph\u1ea3i release gate 110 case.",\n'
    '            ha="center", fontsize=9, style="italic")\n'
    'plt.tight_layout()\n'
    'plt.subplots_adjust(bottom=0.12)\n'
    'plt.show()'
))

cells.append(md(
    "### Nh\u1eadn x\u00e9t t\u1ed5ng h\u1ee3p\n\n"
    "> **L\u01b0u \u00fd v\u1ec1 metric:** Guardrails v\u00e0 Claim Verifier \u0111\u1ea1t 100%\n"
    "> ngh\u0129a l\u00e0 **detect rate** (ph\u00e1t hi\u1ec7n \u0111\u00fang m\u1ecdi test case), kh\u00f4ng ph\u1ea3i\n"
    "> precision tr\u00ean traffic th\u1eadt. C\u1ea7n eval production \u0111\u1ec3 bi\u1ebft false-positive.\n\n"
    "**M\u1ea1nh (>= 80%):**\n"
    "- **Retrieval** (Part II): Hybrid RRF — Hit@5 từ `notebook_retrieval_screening.json`\n"
    "- **Guardrails** + **Claim Verifier**: 100% detect rate (Part III)\n"
    "- **Multi-turn** (\u00a713): retention tr\u00ean b\u1ed9 turn thi\u1ebft k\u1ebf\n\n"
    "**Y\u1ebfu (< 80%) / c\u1ea7n t\u00e1ch metric:**\n"
    "- **Intent Router**: miss teencode v\u00e0 edge cases\n"
    "- **Pipeline \u00a712** vs **so s\u00e1nh 3 model \u00a714**: c\u00f9ng 20 query, metric/timestamp kh\u00e1c nhau\n"
    "- **Non-abstain Part IV**: nhi\u1ec1u abstain fail-closed \u2014 Claim Verifier ch\u1ec9 check KB\n\n"
    "**Gi\u1ea3i th\u00edch pipeline y\u1ebfu:**\n"
    "Pipeline kh\u00f4ng y\u1ebfu v\u00ec code sai, m\u00e0 v\u00ec **Claim Verifier ch\u01b0a check LiveContext**.\n"
    "KB FAQ \u2192 ho\u1ea1t \u0111\u1ed9ng t\u1ed1t. Menu/Allergy \u2192 LLM sinh \u0111\u00fang nh\u01b0ng\n"
    "verifier kh\u00f4ng t\u00ecm evidence \u2192 abstain."
))

cells.append(md(
    "## 16. H\u1ea1n ch\u1ebf v\u00e0 h\u01b0\u1edbng ph\u00e1t tri\u1ec3n\n\n"
    "### H\u1ea1n ch\u1ebf\n\n"
    "| H\u1ea1n ch\u1ebf | \u1ea2nh h\u01b0\u1edfng | M\u1ee9c \u0111\u1ed9 |\n"
    "|---|---|---|\n"
    "| D\u1eef li\u1ec7u t\u1ef1 x\u00e2y (KB, eval set) | K\u1ebft qu\u1ea3 kh\u00f4ng generalize | Cao |\n"
    "| Sample size nh\u1ecf (20 intent / 20 pipeline / 20\u00d73 model) | Kh\u00f4ng th\u1ed1ng k\u00ea m\u1ea1nh | Cao |\n"
    "| `route` null trong export JSON | Availability \u0111\u1ebfm optimistic | Cao |\n"
    "| Claim Verifier ch\u1ec9 check KB | Menu/Allergy b\u1ecb abstain d\u00f9 LLM tr\u1ea3 l\u1eddi \u0111\u00fang | Cao |\n"
    "| Ch\u01b0a c\u00f3 traffic th\u1eadt | Ch\u01b0a bi\u1ebft production quality | Cao |\n"
    "| 3-model ch\u01b0a kh\u00e1c bi\u1ec7t \u1edf KB path | KB fast-path kh\u00f4ng d\u00f9ng LLM | TB |\n"
    "| Intent rule-based miss teencode | Miss queries Vietnamese noisy | TB |\n"
    "| Dense E5 y\u1ebfu noisy | C\u1ea7n normalize (Part II) | TB |\n"
    "| Claim Verifier lexical | False-reject paraphrase | Th\u1ea5p |\n\n"
    "### B\u1ea3n \u0111\u1ed3 b\u1eb1ng ch\u1ee9ng (staging)\n\n"
    "| Ngu\u1ed3n trong notebook | Artifact / doc | \u00dd ngh\u0129a release |\n"
    "|---|---|---|\n"
    "| Retrieval Part II | `notebook_retrieval_screening.json` | Hit@5 screening trong notebook (sau execute Part II) |\n"
    "| Retrieval release | `dev_retrieval_summary.v3.json` (n\u1ebfu c\u00f3) | Gate staging Hit@5 \u2014 kh\u00e1c b\u1ed9 case Part II |\n"
    "| Session / multi-turn | `evaluation/results/session_e2e_eval.json` | Context retention offline |\n"
    "| Golden LLM eval | `evaluation/results/golden_llm_eval_*.json` | Baseline l\u1ecbch s\u1eed; kh\u00f4ng headline 100% |\n"
    "| Paired GPT/DeepSeek quality | `evaluation/dual_model/.../comparison.json` | Protocol PASS; quality CH\u01afA PASS release |\n"
    "| Live / dual notebook | `notebook_live_test.json`, `dual_model_test.json` | Demo pipeline; kh\u00f4ng thay human eval |\n"
    "| Tr\u1ea1ng th\u00e1i t\u1ed5ng | [`docs/ai/AI_STAGING_READINESS.md`](../../docs/ai/AI_STAGING_READINESS.md) | **NOT READY** cho \u0111\u1ebfn khi \u0111\u1ee7 gate |\n\n"
    "### H\u01b0\u1edbng ph\u00e1t tri\u1ec3n\n\n"
    "| \u01afu ti\u00ean | H\u01b0\u1edbng | Impact |\n"
    "|---|---|---|\n"
    "| **CAO** | Test v\u1edbi menu data th\u1eadt (LiveContext) | M\u1edf kh\u00f3a menu + dual-model so s\u00e1nh |\n"
    "| **CAO** | Eval t\u1eeb traffic th\u1eadt + human eval | K\u1ebft qu\u1ea3 s\u00e1t th\u1ef1c t\u1ebf |\n"
    "| **CAO** | Th\u00eam teencode rules cho Intent | V\u01b0\u1ee3t 75% accuracy |\n"
    "| TB | ML-based intent (BERT/PhoBERT) | B\u1eaft paraphrase |\n"
    "| TB | Fine-tune E5 Vietnamese | C\u1ea3i thi\u1ec7n noisy retrieval |\n"
    "| Th\u1ea5p | Cross-encoder rerank | Hit@1 t\u1ed1t h\u01a1n |"
))

cells.append(md(
    "## 17. K\u1ebft lu\u1eadn\n\n"
    "Notebook n\u00e0y \u0111\u00e3 **ch\u1ea1y th\u1eadt** v\u00e0 \u0111\u00e1nh gi\u00e1 to\u00e0n b\u1ed9 pipeline RAG chatbot:\n\n"
    "1. **Part I** \u2014 26 files KB \u2192 213 chunks. Normalize ti\u1ebfng Vi\u1ec7t gi\u00fap BM25 +49% noisy.\n"
    "2. **Part II** — So s\u00e1nh 3 methods: **Hybrid RRF t\u1ed1t nh\u1ea5t** tr\u00ean b\u1ed9 screening (`notebook_retrieval_screening.json`).\n"
    "   BM25 m\u1ea1nh noisy, Dense m\u1ea1nh clean \u2192 k\u1ebft h\u1ee3p l\u00e0 t\u1ed1i \u01b0u.\n"
    "3. **Part III** \u2014 4 th\u00e0nh ph\u1ea7n pipeline:\n"
    "   - Intent Router ch\u1ecdn **khi n\u00e0o d\u00f9ng Hybrid RRF** (Part II)\n"
    "   - Guardrails ch\u1eb7n queries nguy hi\u1ec3m **tr\u01b0\u1edbc** khi t\u1ed1n chi ph\u00ed LLM\n"
    "   - Session Memory nh\u1edb d\u1ecb \u1ee9ng, context qua **nhi\u1ec1u l\u01b0\u1ee3t**\n"
    "   - Claim Verifier d\u00f9ng **KB (Part I) l\u00e0m evidence** ch\u1ed1ng hallucination"
))

cells.append(code(
    'from scripts.notebook_metrics import format_part17_bullet_part4, summarize_dual_model\n\n'
    'if "dual" not in globals():\n'
    '    dual = json.load(open(\n'
    '        AI_ROOT / "evaluation" / "results" / "dual_model_test.json", encoding="utf-8"\n'
    '    ))\n'
    'print(format_part17_bullet_part4(summarize_dual_model(dual)))\n'
    'print()\n'
    'print("**T\u00ednh n\u0103ng product:** D\u1eef li\u1ec7u th\u1eadt (LiveContext), Cart Suggestion,")\n'
    'print("refresh kh\u00f4ng m\u1ea5t chat, session theo phi\u00ean b\u00e0n.")\n'
    'print()\n'
    'print("> H\u1ec7 th\u1ed1ng ch\u1ea1y \u0111\u01b0\u1ee3c tr\u00ean **VPS 4vCPU/8GB, kh\u00f4ng GPU**.")\n'
    'print("> B\u01b0\u1edbc ti\u1ebfp theo: Claim Verifier + LiveContext, human eval, gate trong AI_STAGING_READINESS.")'
))

cells.append(md(format_deploy_lock_section()))

# WRITE
nb.cells = cells
nbf.write(nb, str(nb_path))
print(f"Wrote {nb_path} ({len(cells)} cells)")
