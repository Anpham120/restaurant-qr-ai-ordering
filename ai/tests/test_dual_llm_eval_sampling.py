from __future__ import annotations

import unittest

from evaluation.golden_eval_common import DEFAULT_STRATIFIED_SAMPLING_SEED
from evaluation.run_dual_llm_eval import (
    _build_eval_args,
    _build_parser,
    _generation_input_fidelity,
    _retrieval_pipeline_fidelity,
    _sampling_protocol,
)


class DualLlmEvalSamplingTests(unittest.TestCase):
    def test_dual_runner_defaults_to_seeded_stratified_sampling(self) -> None:
        args = _build_parser().parse_args([])

        self.assertEqual("stratified", args.sampling_strategy)
        self.assertEqual(DEFAULT_STRATIFIED_SAMPLING_SEED, args.sampling_seed)

    def test_each_profile_receives_identical_sampling_arguments(self) -> None:
        args = _build_parser().parse_args(
            [
                "--split",
                "dev",
                "--limit",
                "12",
                "--sampling-strategy",
                "stratified",
                "--sampling-seed",
                "91",
            ]
        )

        first = _build_eval_args(args, output="gpt55.json")
        second = _build_eval_args(args, output="deepseek.json")

        def sampling_values(values: list[str]) -> tuple[str, str]:
            strategy_index = values.index("--sampling-strategy")
            seed_index = values.index("--sampling-seed")
            return values[strategy_index + 1], values[seed_index + 1]

        self.assertEqual(("stratified", "91"), sampling_values(first))
        self.assertEqual(sampling_values(first), sampling_values(second))

    def test_protocol_contains_distribution_and_case_set_hash(self) -> None:
        args = _build_parser().parse_args(["--split", "dev", "--limit", "12"])

        protocol = _sampling_protocol(args)

        self.assertEqual("stratified", protocol["sampling_strategy"])
        self.assertEqual(DEFAULT_STRATIFIED_SAMPLING_SEED, protocol["sampling_seed"])
        self.assertEqual(12, sum(protocol["family_distribution"].values()))
        self.assertEqual(12, len(protocol["family_distribution"]))
        self.assertRegex(protocol["case_set_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(protocol["case_order_sha256"], r"^[0-9a-f]{64}$")

    def test_pipeline_fidelity_rejects_fallback_or_runtime_mismatch(self) -> None:
        faithful = _retrieval_pipeline_fidelity(
            {
                "retriever_runtime": {
                    "same_runtime": True,
                    "fallback_present": False,
                    "by_profile": {
                        "gpt55": {
                            "requested_method": "hybrid",
                            "effective_method": "hybrid",
                            "fallback_used": False,
                        },
                        "deepseek": {
                            "requested_method": "hybrid",
                            "effective_method": "hybrid",
                            "fallback_used": False,
                        },
                    },
                }
            }
        )
        fallback = _retrieval_pipeline_fidelity(
            {
                "retriever_runtime": {
                    "same_runtime": True,
                    "fallback_present": True,
                    "by_profile": {
                        "gpt55": {
                            "requested_method": "hybrid",
                            "effective_method": "bm25-fallback",
                            "fallback_used": True,
                        },
                        "deepseek": {
                            "requested_method": "hybrid",
                            "effective_method": "bm25-fallback",
                            "fallback_used": True,
                        },
                    },
                }
            }
        )

        self.assertTrue(faithful["pass"])
        self.assertFalse(fallback["pass"])
        self.assertFalse(fallback["requested_matches_effective"])

    def test_generation_fidelity_requires_hash_and_config_parity(self) -> None:
        faithful = _generation_input_fidelity(
            {
                "generation_input_parity": {
                    "common_llm_called_pair_count": 2,
                    "verifiable_pair_count": 2,
                    "matching_pair_count": 2,
                    "missing_pair_count": 0,
                    "mismatching_pair_count": 0,
                    "same_generation_config": True,
                    "pass": True,
                }
            }
        )
        mismatch = _generation_input_fidelity(
            {
                "generation_input_parity": {
                    "common_llm_called_pair_count": 2,
                    "verifiable_pair_count": 2,
                    "matching_pair_count": 1,
                    "missing_pair_count": 0,
                    "mismatching_pair_count": 1,
                    "same_generation_config": True,
                    "pass": False,
                }
            }
        )

        self.assertTrue(faithful["pass"])
        self.assertFalse(mismatch["pass"])


if __name__ == "__main__":
    unittest.main()
