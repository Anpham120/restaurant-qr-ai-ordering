"""Controlled comparison of the three production pipeline profiles.

The runner fixes model, menu, knowledge base, retrieval configuration and prompt
budget, then writes the only artifact production is allowed to select from.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import subprocess
import sys
import time
import unicodedata
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from app.clients.router import RouterClient  # noqa: E402
from app.config import (  # noqa: E402
    DEFAULT_RATE_LIMIT_FALLBACK_MODEL,
    AiServiceConfig,
    PIPELINE_PROFILES,
    load_config,
)
from app.services.assistant import AiAssistantService  # noqa: E402
from evaluation.golden_eval_common import load_menu_items  # noqa: E402
from evaluation.pipeline_selection import select_winner  # noqa: E402
from evaluation.research_inputs import compute_research_input_hash  # noqa: E402

DEEPSEEK_MODEL = "oc/deepseek-v4-flash-free"
PROFILE_ORDER = ("llm_first_v1", "evidence_first_v2", "planner_state_v3")
DATASET_PATH = AI_ROOT / "evaluation" / "pipeline_profile_cases.json"
DEFAULT_OUTPUT_PATH = AI_ROOT / "evaluation" / "results" / "pipeline_selection.json"


def create_eval_router_client(config: AiServiceConfig) -> RouterClient:
    return RouterClient(
        config.base_url,
        config.api_key,
        config.model,
        config.llm_timeout_seconds,
        max_retry=config.max_retry,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        fallback_model=config.rate_limit_fallback_model,
        fallback_enabled=config.rate_limit_fallback_enabled,
    )


def required_runs(llm_calls: int) -> int:
    """Factual deterministic paths run once; any DeepSeek path runs three times."""

    return 1 if llm_calls == 0 else 3


def _normalized(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(text.split())


def _observed_menu_ids(response: dict[str, Any]) -> set[str]:
    ids = {
        str(item_id)
        for item_id in response.get("resolved_menu_item_ids") or []
        if item_id
    }
    ids.update(
        str(action.get("menu_item_id"))
        for action in response.get("suggested_cart_actions") or []
        if action.get("menu_item_id")
    )
    ids.update(
        str(item.get("menu_item_id"))
        for item in response.get("evidence") or []
        if item.get("menu_item_id")
    )
    return ids


def _evidence_ids(response: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for evidence in response.get("evidence") or []:
        for key in ("menu_item_id", "chunk_id"):
            value = evidence.get(key)
            if value:
                ids.add(str(value))
    return ids


def score_case(
    case: dict[str, Any],
    response: dict[str, Any],
    *,
    allowed_menu_ids: set[str],
) -> dict[str, Any]:
    """Strict, deterministic score used identically for every profile."""

    content = _normalized(response.get("content"))
    observed_ids = _observed_menu_ids(response)
    evidence_ids = _evidence_ids(response)
    expected_ids = {str(value) for value in case.get("expected_menu_ids") or []}
    forbidden_ids = {str(value) for value in case.get("forbidden_menu_ids") or []}
    match_mode = str(case.get("match") or "any")

    if expected_ids:
        menu_pass = (
            expected_ids <= observed_ids
            if match_mode == "all"
            else bool(expected_ids & observed_ids)
        )
    else:
        menu_pass = True

    contains_all = [
        _normalized(value) for value in case.get("content_contains_all") or []
    ]
    contains_any = [
        _normalized(value) for value in case.get("content_contains_any") or []
    ]
    forbidden_content = [
        _normalized(value) for value in case.get("content_forbids") or []
    ]
    content_pass = all(value in content for value in contains_all)
    if contains_any:
        content_pass = content_pass and any(value in content for value in contains_any)
    content_pass = content_pass and not any(
        value in content for value in forbidden_content
    )

    claims = list(response.get("claims") or [])
    unsupported_claims = sum(
        1
        for claim in claims
        if not bool(claim.get("verified"))
        and _normalized(claim.get("text"))
        and _normalized(claim.get("text")) in content
    )
    claim_evidence_ids = {
        str(evidence_id)
        for claim in claims
        if bool(claim.get("verified"))
        for evidence_id in claim.get("evidence_ids") or []
        if evidence_id
    }
    allowed_evidence_only = (
        observed_ids <= allowed_menu_ids
        and claim_evidence_ids <= (evidence_ids | allowed_menu_ids)
    )
    id_price_passed = not bool(observed_ids & forbidden_ids)
    expected_flags = set(case.get("required_guardrail_flags") or [])
    flags = set(response.get("guardrail_flags") or [])
    flags_pass = expected_flags <= flags
    decision = response.get("decision") or {}
    response_usable = (
        decision.get("route") != "abstain"
        and not flags.intersection(
            {
                "EVIDENCE_INSUFFICIENT",
                "UNSUPPORTED_CLAIM_BLOCKED",
                "AI_PROVIDER_UNAVAILABLE",
            }
        )
    )

    persisted_values = [
        _normalized(fact.get("value"))
        for fact in (response.get("session_updates") or {}).get("facts") or []
    ]
    assistant_text_not_persisted = not any(
        value and (value == content or value in content and len(value) > 40)
        for value in persisted_values
    )

    strict = (
        menu_pass
        and content_pass
        and unsupported_claims == 0
        and allowed_evidence_only
        and id_price_passed
        and flags_pass
        and response_usable
    )
    safety_success = (
        content_pass
        and unsupported_claims == 0
        and allowed_evidence_only
        and id_price_passed
        and flags_pass
    )
    return {
        "id": str(case.get("id") or ""),
        "strict_semantic_success": strict,
        "safety_success": safety_success,
        "menu_pass": menu_pass,
        "content_pass": content_pass,
        "unsupported_claims": unsupported_claims,
        "allowed_evidence_only": allowed_evidence_only,
        "id_price_passed": id_price_passed,
        "allergy_passed": flags_pass
        if case.get("category") == "allergy"
        else True,
        "assistant_text_not_persisted": assistant_text_not_persisted,
        "observed_menu_ids": sorted(observed_ids),
        "response_path": (response.get("latency_ms") or {}).get("path"),
        "provider_available": bool(response.get("provider_available")),
        "response_usable": response_usable,
        "verifier_result": response.get("verifier_result"),
    }


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _p95(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def aggregate_profile(
    profile: str,
    runs: list[dict[str, Any]],
    *,
    session_isolation_passed: bool,
    availability_passed: bool,
) -> dict[str, Any]:
    scores = [run["score"] for run in runs]
    by_case: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_case.setdefault(str(run.get("case_id") or ""), []).append(run)
    repeated_cases = [case_runs for case_runs in by_case.values() if len(case_runs) > 1]
    disagreement_count = 0
    for case_runs in repeated_cases:
        signatures = {
            (
                bool(run["score"]["strict_semantic_success"]),
                tuple(run["score"]["observed_menu_ids"]),
                str(run["score"].get("response_path") or ""),
            )
            for run in case_runs
        }
        if len(signatures) > 1:
            disagreement_count += 1
    safety_scores = [
        run["score"]
        for run in runs
        if run.get("category") in {"safety", "allergy"}
    ]
    total_llm_calls = sum(int(run.get("llm_calls") or 0) for run in runs)
    successful_llm_calls = sum(
        int(run.get("successful_llm_calls") or 0) for run in runs
    )
    model_attempts = [
        attempt
        for run in runs
        for attempt in (run.get("model_attempts") or [])
    ]
    attempts_by_model: dict[str, int] = {}
    successes_by_model: dict[str, int] = {}
    failures_by_model: dict[str, int] = {}
    for attempt in model_attempts:
        model = str(attempt.get("model") or "")
        if not model:
            continue
        attempts_by_model[model] = attempts_by_model.get(model, 0) + 1
        target = (
            successes_by_model
            if attempt.get("outcome") == "success"
            else failures_by_model
        )
        target[model] = target.get(model, 0) + 1
    fallback_count = sum(
        1
        for attempt in model_attempts
        if attempt.get("role") == "rate_limit_fallback"
    )
    model_usage = {
        "attempts_by_model": dict(sorted(attempts_by_model.items())),
        "successes_by_model": dict(sorted(successes_by_model.items())),
        "failures_by_model": dict(sorted(failures_by_model.items())),
        "fallback_count": fallback_count,
        "fallback_rate": (
            fallback_count / total_llm_calls
            if total_llm_calls
            else 0.0
        ),
        "logical_llm_operations": total_llm_calls,
    }
    deepseek_calls_attempted = (
        attempts_by_model.get(DEEPSEEK_MODEL, 0)
        if model_attempts
        else total_llm_calls
    )
    deepseek_calls_successful = (
        successes_by_model.get(DEEPSEEK_MODEL, 0)
        if model_attempts
        else successful_llm_calls
    )
    metrics = {
        "strict_semantic_success": _mean(
            float(score["strict_semantic_success"]) for score in scores
        ),
        "context_accuracy": _mean(
            float(run.get("context_accuracy", 1.0)) for run in runs
        ),
        "p95_latency_ms": _p95(run.get("latency_ms", 0.0) for run in runs),
        "mean_llm_calls": _mean(float(run.get("llm_calls", 0)) for run in runs),
        "run_to_run_disagreement_rate": (
            disagreement_count / len(repeated_cases) if repeated_cases else 0.0
        ),
        "llm_case_count": len(repeated_cases),
        "deterministic_case_count": sum(
            1 for case_runs in by_case.values() if len(case_runs) == 1
        ),
        "unsupported_claims": sum(
            int(score["unsupported_claims"]) for score in scores
        ),
        "allowed_evidence_only": all(
            bool(score["allowed_evidence_only"]) for score in scores
        ),
        "allergy_passed": all(
            bool(score["allergy_passed"])
            for score in scores
            if score["id"]
        ),
        "id_price_passed": all(
            bool(score["id_price_passed"]) for score in scores
        ),
        "session_isolation_passed": session_isolation_passed,
        "assistant_text_not_persisted": all(
            bool(score["assistant_text_not_persisted"]) for score in scores
        ),
        "availability_passed": availability_passed,
        "model_usage": model_usage,
        "provider_calls_succeeded": (
            total_llm_calls > 0 and successful_llm_calls > 0
        ),
        "deepseek_calls_attempted": deepseek_calls_attempted,
        "deepseek_calls_successful": deepseek_calls_successful,
        "deepseek_call_success_rate": (
            deepseek_calls_successful / deepseek_calls_attempted
            if deepseek_calls_attempted
            else 0.0
        ),
        "deepseek_calls_succeeded": (
            deepseek_calls_attempted > 0 and deepseek_calls_successful > 0
        ),
    }
    metrics["safety_passed"] = (
        all(bool(score["safety_success"]) for score in safety_scores)
        and metrics["id_price_passed"]
        and availability_passed
    )
    return {"profile": profile, "metrics": metrics, "runs": runs}


def build_selection_artifact(
    *,
    profile_results: list[dict[str, Any]],
    commit_sha: str,
    research_input_hash: str,
    dataset_hash: str,
    generated_at: str,
    working_tree_dirty: bool = False,
) -> dict[str, Any]:
    selection = select_winner(profile_results)
    return {
        "schema_version": "pipeline-selection-v3",
        "model": DEEPSEEK_MODEL,
        "model_policy": {
            "primary_model": DEEPSEEK_MODEL,
            "fallback_model": DEFAULT_RATE_LIMIT_FALLBACK_MODEL,
            "fallback_enabled": True,
            "fallback_trigger": "http_429",
            "max_fallbacks_per_operation": 1,
        },
        "profiles": profile_results,
        "winner": selection["winner"],
        "selection_reason": selection["selection_reason"],
        "rejected_by_safety": selection["rejected_by_safety"],
        "commit_sha": commit_sha,
        "research_commit_sha": commit_sha,
        "research_input_hash": research_input_hash,
        "working_tree_dirty": working_tree_dirty,
        "dataset_hash": dataset_hash,
        "generated_at": generated_at,
    }


class CountingClient:
    def __init__(self, delegate: RouterClient) -> None:
        self.delegate = delegate
        self.calls = 0
        self.successful_calls = 0

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        self.calls += 1
        result = await self.delegate.complete(messages)
        self.successful_calls += 1
        return result

    async def complete_structured(self, *args: Any, **kwargs: Any) -> str | None:
        self.calls += 1
        result = await self.delegate.complete_structured(*args, **kwargs)
        self.successful_calls += 1
        return result


class _UnavailableClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str | None:
        raise TimeoutError("availability probe")

    async def complete_structured(self, *_args: Any, **_kwargs: Any) -> str | None:
        raise TimeoutError("availability probe")


class _MalformedClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str | None:
        return "{not-valid-json"

    async def complete_structured(self, *_args: Any, **_kwargs: Any) -> str | None:
        return "{not-valid-json"


def _blank_state() -> dict[str, Any]:
    return {
        "facts": [],
        "constraints": {},
        "referenced_menu_item_ids": [],
        "suggested_menu_item_ids": [],
        "rejected_menu_item_ids": [],
        "accepted_menu_item_ids": [],
        "added_to_cart_menu_item_ids": [],
        "rolling_summary": "",
        "memory_version": "v2",
        "conversation_frame": {"turn_sequence": 0},
    }


def _next_state(response: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    updates = response.get("session_updates") or {}
    result = dict(previous)
    for key in (
        "facts",
        "constraints",
        "referenced_menu_item_ids",
        "suggested_menu_item_ids",
        "rejected_menu_item_ids",
        "accepted_menu_item_ids",
        "added_to_cart_menu_item_ids",
        "rolling_summary",
        "memory_version",
        "conversation_frame",
    ):
        if key in updates:
            result[key] = updates[key]
    return result


async def _run_trial(
    service: AiAssistantService,
    client: CountingClient,
    case: dict[str, Any],
    menu_items: list[dict[str, Any]],
    allowed_ids: set[str],
    trial: int,
) -> dict[str, Any]:
    state = _blank_state()
    history: list[dict[str, Any]] = []
    turn_scores: list[dict[str, Any]] = []
    context_checks = 0
    context_passes = 0
    before_calls = client.calls
    before_successful_calls = client.successful_calls
    started = time.perf_counter()
    turns = case.get("turns") or [
        {
            "message": case["message"],
            **{key: value for key, value in case.items() if key not in {"turns"}},
        }
    ]
    last_response: dict[str, Any] = {}

    for turn_index, turn in enumerate(turns):
        service.invalidate_cache()
        last_response = await service.chat(
            {
                "contract_version": "v2",
                "message": turn["message"],
                "pipeline_profile": service._config.pipeline_profile,
                "history": history[-12:],
                "session_id": f"{case['id']}-trial-{trial}",
                "session_state": state,
                "live_context": {
                    "catalog_version": "pipeline-eval-menu-v1",
                    "menu_items": menu_items,
                    "table_code": "T01",
                },
            }
        )
        turn_scores.append(score_case(turn, last_response, allowed_menu_ids=allowed_ids))
        state = _next_state(last_response, state)
        for key, value in (turn.get("expected_constraints") or {}).items():
            context_checks += 1
            if state.get("constraints", {}).get(key) == value:
                context_passes += 1
        expected_focus = set(turn.get("expected_focus_menu_ids") or [])
        if expected_focus:
            context_checks += 1
            observed_focus = set(
                (state.get("conversation_frame") or {}).get("focus_menu_item_ids")
                or []
            )
            if expected_focus <= observed_focus:
                context_passes += 1
        history.extend(
            [
                {"role": "user", "content": turn["message"]},
                {
                    "role": "assistant",
                    "content": last_response.get("content") or "",
                    "suggested_cart_actions": last_response.get(
                        "suggested_cart_actions"
                    )
                    or [],
                },
            ]
        )

    latency_ms = (time.perf_counter() - started) * 1000
    combined_score = {
        **turn_scores[-1],
        "strict_semantic_success": all(
            bool(item["strict_semantic_success"]) for item in turn_scores
        ),
        "safety_success": all(bool(item["safety_success"]) for item in turn_scores),
        "unsupported_claims": sum(
            int(item["unsupported_claims"]) for item in turn_scores
        ),
        "allowed_evidence_only": all(
            bool(item["allowed_evidence_only"]) for item in turn_scores
        ),
        "id_price_passed": all(bool(item["id_price_passed"]) for item in turn_scores),
        "allergy_passed": all(bool(item["allergy_passed"]) for item in turn_scores),
        "assistant_text_not_persisted": all(
            bool(item["assistant_text_not_persisted"]) for item in turn_scores
        ),
    }
    return {
        "case_id": case["id"],
        "category": case.get("category", "single_turn"),
        "trial": trial,
        "llm_calls": client.calls - before_calls,
        "successful_llm_calls": client.successful_calls - before_successful_calls,
        "latency_ms": round(latency_ms, 3),
        "context_accuracy": (
            context_passes / context_checks if context_checks else 1.0
        ),
        "score": combined_score,
        "turn_scores": turn_scores,
        "final_state": state,
        "pipeline_profile": last_response.get("pipeline_profile"),
        "model": last_response.get("model"),
        "model_attempts": last_response.get("model_attempts") or [],
    }


async def _availability_probe(config: Any, profile: str, menu_items: list[dict[str, Any]]) -> bool:
    for label, client in (
        ("timeout", _UnavailableClient()),
        ("malformed_json", _MalformedClient()),
    ):
        service = AiAssistantService(
            replace(config, pipeline_profile=profile),
            llm_client=client,
        )
        response = await service.chat(
            {
                "message": "Hãy tư vấn một thực đơn cân bằng cho buổi gặp mặt.",
                "pipeline_profile": profile,
                "history": [],
                "session_state": _blank_state(),
                "menu_items": menu_items,
                "session_id": f"availability-{label}-{profile}",
            }
        )
        score = score_case(
            {"id": f"availability-{label}"},
            response,
            allowed_menu_ids={
                str(item["id"])
                for item in menu_items
                if bool(item.get("is_available", True))
            },
        )
        safe = (
            score["unsupported_claims"] == 0
            and score["allowed_evidence_only"]
            and score["id_price_passed"]
        )
        if not safe:
            return False
    return True


def _session_isolation(runs: list[dict[str, Any]]) -> bool:
    isolated = [
        run
        for run in runs
        if run.get("case_id") in {"session_a_allergy", "session_b_clean"}
        and run.get("trial") == 1
    ]
    if len(isolated) != 2:
        return False
    states = {run["case_id"]: run["final_state"] for run in isolated}
    allergy_state = json.dumps(states["session_a_allergy"], ensure_ascii=False).casefold()
    clean_state = json.dumps(states["session_b_clean"], ensure_ascii=False).casefold()
    return (
        ("đậu phộng" in allergy_state or "dau phong" in allergy_state)
        and "đậu phộng" not in clean_state
        and "dau phong" not in clean_state
    )


async def evaluate_profiles(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    base_config = replace(
        load_config(),
        model=DEEPSEEK_MODEL,
        knowledge_base_path=AI_ROOT / "knowledge-base",
        rate_limit_fallback_model=DEFAULT_RATE_LIMIT_FALLBACK_MODEL,
        rate_limit_fallback_enabled=True,
    )
    if not base_config.api_key:
        raise RuntimeError("LLM_API_KEY is required for controlled pipeline selection")

    menu_items = load_menu_items()
    allowed_ids = {
        str(item["id"]) for item in menu_items if bool(item.get("is_available", True))
    }
    async def evaluate_profile(profile: str) -> dict[str, Any]:
        profile_config = replace(base_config, pipeline_profile=profile)
        delegate = create_eval_router_client(profile_config)
        client = CountingClient(delegate)
        service = AiAssistantService(
            profile_config,
            llm_client=client,
        )
        profile_runs: list[dict[str, Any]] = []
        for case in dataset["cases"]:
            first = await _run_trial(
                service, client, case, menu_items, allowed_ids, trial=1
            )
            profile_runs.append(first)
            for trial in range(2, required_runs(first["llm_calls"]) + 1):
                profile_runs.append(
                    await _run_trial(
                        service, client, case, menu_items, allowed_ids, trial=trial
                    )
                )
        availability_passed = await _availability_probe(
            base_config, profile, menu_items
        )
        return aggregate_profile(
            profile,
            profile_runs,
            session_isolation_passed=_session_isolation(profile_runs),
            availability_passed=availability_passed,
        )

    # Profiles are independent experimental arms. Running them concurrently
    # keeps wall-clock time bounded without changing prompts, datasets or budgets.
    results = await asyncio.gather(
        *(evaluate_profile(profile) for profile in PROFILE_ORDER)
    )
    return list(results)


def _dataset_hash(dataset_path: Path) -> str:
    digest = hashlib.sha256()
    for path in (dataset_path, PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"):
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _commit_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


async def _main(args: argparse.Namespace) -> int:
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    unknown = set(PROFILE_ORDER) - set(PIPELINE_PROFILES)
    if unknown:
        raise RuntimeError(f"Runtime does not implement profiles: {sorted(unknown)}")
    profile_results = await evaluate_profiles(dataset)
    artifact = build_selection_artifact(
        profile_results=profile_results,
        commit_sha=_commit_sha(),
        research_input_hash=compute_research_input_hash(PROJECT_ROOT),
        dataset_hash=_dataset_hash(args.dataset),
        generated_at=datetime.now(timezone.utc).isoformat(),
        working_tree_dirty=_working_tree_dirty(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "winner": artifact["winner"],
            "selection_reason": artifact["selection_reason"],
            "output": str(args.output),
        },
        ensure_ascii=False,
    ))
    return 0 if artifact["winner"] else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(parse_args())))
