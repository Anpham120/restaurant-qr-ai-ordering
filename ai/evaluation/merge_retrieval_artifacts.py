"""Merge memory-isolated retrieval runs into one validated comparison artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluation.retrieval_comparison import compare_retrieval_results
from evaluation.run_retrieval_experiment import DEFAULT_METHODS


def merge_artifact_payloads(
    sources: Sequence[tuple[str, dict[str, Any]]],
    *,
    expected_methods: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Validate and merge single-method artifacts, then recompute paired tests."""

    expected = tuple(expected_methods or (method.value for method in DEFAULT_METHODS))
    if not sources:
        raise ValueError("at least one source artifact is required")

    methods: dict[str, dict[str, Any]] = {}
    signatures: list[dict[str, Any]] = []
    registries: list[str] = []
    for label, payload in sources:
        source_methods = payload.get("methods")
        if not isinstance(source_methods, dict) or len(source_methods) != 1:
            raise ValueError(f"{label}: expected exactly one measured method")
        method_name, method_result = next(iter(source_methods.items()))
        if method_name in methods:
            raise ValueError(f"duplicate method artifact: {method_name}")
        if not isinstance(method_result, dict) or method_result.get("method") != method_name:
            raise ValueError(f"{label}: method identity mismatch")
        methods[method_name] = method_result
        signatures.append(_compatibility_signature(payload, method_result))
        registries.append(_canonical_json(payload.get("encoder_registry") or {}))

    if set(methods) != set(expected):
        missing = sorted(set(expected) - set(methods))
        extra = sorted(set(methods) - set(expected))
        raise ValueError(f"method set mismatch; missing={missing}, extra={extra}")
    if len({_canonical_json(signature) for signature in signatures}) != 1:
        _raise_signature_mismatch(signatures)
    if len(set(registries)) != 1:
        raise ValueError("encoder registry mismatch across source artifacts")

    signature = signatures[0]
    ordered_methods = {name: methods[name] for name in sorted(methods)}
    top_k = int(signature["top_k"])
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": signature["split"],
        "top_k": top_k,
        "methods": ordered_methods,
        "encoder_registry": json.loads(registries[0]),
        "screening_protocol": {
            "execution": "isolated-single-method",
            "reason": "bound peak memory and make encoder failures attributable",
            "latency_repetitions": signature["latency_repetitions"],
            "latency_claim_scope": (
                "screening-only" if signature["latency_repetitions"] < 7 else "release-candidate"
            ),
        },
        "method_order_protocol": {
            "strategy": "merged-isolated-single-method",
            "execution_order": list(ordered_methods),
        },
        "pairwise_statistics": compare_retrieval_results(
            ordered_methods,
            cutoff=max(value for value in (1, 3, 5, 10) if value <= top_k),
        ),
        "experiment_profile": {
            "name": "all-research-encoders-isolated",
            "measured_methods": list(ordered_methods),
            "not_measured_methods": [],
        },
    }


def _compatibility_signature(
    payload: dict[str, Any],
    method_result: dict[str, Any],
) -> dict[str, Any]:
    dataset = method_result.get("dataset") or {}
    corpus = method_result.get("corpus") or {}
    latency_protocol = (method_result.get("latency_ms") or {}).get("protocol") or {}
    return {
        "split": payload.get("split"),
        "top_k": payload.get("top_k"),
        "corpus_sha256": corpus.get("corpus_sha256"),
        "family_source_sha256": dataset.get("family_source_sha256"),
        "materialized_cases_sha256": dataset.get("materialized_cases_sha256"),
        "latency_repetitions": latency_protocol.get("repetitions_per_query"),
    }


def _raise_signature_mismatch(signatures: Sequence[dict[str, Any]]) -> None:
    fields = signatures[0]
    mismatched = [
        field
        for field in fields
        if len({_canonical_json(signature.get(field)) for signature in signatures}) != 1
    ]
    readable = {
        "corpus_sha256": "corpus",
        "latency_repetitions": "latency repetitions",
    }
    labels = [readable.get(field, field.replace("_", " ")) for field in mismatched]
    raise ValueError("incompatible source artifacts: " + ", ".join(labels))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    sources = []
    source_meta = []
    for path in args.inputs:
        raw = path.read_bytes()
        sources.append((str(path), json.loads(raw.decode("utf-8"))))
        source_meta.append(
            {
                "path": str(path).replace("\\", "/"),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    merged = merge_artifact_payloads(sources)
    merged["source_artifacts"] = source_meta
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
