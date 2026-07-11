# Academic Retrieval Study

This directory is the reproducible research pipeline for the restaurant chatbot.

## Protocol

1. `build_dataset.py` parses the canonical C# seed and fails unless it finds exactly 91 unique menu items and 13 categories.
2. Variants belonging to the same menu item are assigned to the same split.
3. Development data is used for hyper-parameters and abstention thresholds.
4. The locked test set is used for the final report only.
5. TF-IDF, BM25, multilingual dense embedding, BM25+dense RRF and TF-IDF+dense RRF use the same documents and qrels.
6. Production selection uses macro slice nDCG@10. Methods within 0.005 use lower P95 latency as the tie-breaker.
7. Raw per-query rows, checksums, environment metadata, bootstrap intervals and McNemar tests are persisted under `artifacts/`.

## Reproduce

```bash
python -m pip install -r ai/requirements-research.txt
PYTHONPATH=ai python ai/research/build_dataset.py
PYTHONPATH=ai python ai/research/run_experiments.py
MPLCONFIGDIR=/tmp/matplotlib PYTHONPATH=ai python ai/research/build_notebook.py
```

The embedding model is `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through FastEmbed/ONNX. The exact ONNX SHA-256 used for a run is recorded in `artifacts/environment.json`.

The committed results are evidence for the current menu snapshot, not a timeless claim. Any menu, qrel, model or code change must create a new experiment run.

