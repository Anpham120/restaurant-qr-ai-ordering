# TDD evidence: AI context and guardrail regressions

Source plan: user journeys and acceptance criteria derived during the production
repair on 2026-07-26; no external plan file was used.

## User journeys

1. As a Vietnamese guest, I can say "gợi ý hai món" and receive two cards.
2. As a guest, I can ask "món thứ hai giá bao nhiêu?" and receive the price
   for the second card I was shown, not an arbitrary recent dish.
3. As an operator, the canonical safety catalogue verifies the exact flag
   emitted by the deterministic prompt-injection guardrail.

## RED → GREEN evidence

| Guarantee | Test target | RED | GREEN |
| --- | --- | --- | --- |
| Vietnamese word count limits cards | `test_conversation_policy.py::test_vietnamese_word_count_limits_recommendations` | `requested_count` was `None` | Passed after deterministic word-count parsing |
| Ordinal price refers to second displayed dish | `test_assistant_llm_first.py::test_price_for_second_suggested_dish_uses_second_item_in_order` | Resolver returned `m_050`, not `m_009` | Passed after ordered-card ordinal resolution |
| Canonical injection case expects runtime flag | `test_canonical_research_data.py::test_pipeline_runner_receives_cases_adapted_only_from_the_catalogue` | Manifest projected `PROMPT_INJECTION` | Passed after aligning it to `PROMPT_INJECTION_BLOCKED` |

RED command (with the repository Python import path):

```powershell
$env:PYTHONPATH='ai'; py -3 -m pytest ai/tests/test_conversation_policy.py ai/tests/test_assistant_llm_first.py ai/tests/test_canonical_research_data.py -q
```

Result: 3 intended failures, 23 passing tests.

GREEN and focused integration command:

```powershell
$env:PYTHONPATH='ai'; py -3 -m pytest ai/tests/test_conversation_policy.py ai/tests/test_assistant_llm_first.py ai/tests/test_canonical_research_data.py ai/tests/test_prompt_injection_guardrail.py ai/tests/test_pipeline_profile_eval.py ai/tests/test_pipeline_selection.py ai/tests/test_verify_pipeline_selection.py ai/tests/test_ai_ops_deploy_contract.py -q
```

Result: `56 passed, 15 subtests passed in 1.35s`.

## Coverage and limits

The current Python runtime does not expose `pytest-cov` (`pytest --help` has no
`--cov` option), so a numerical coverage percentage was not invented. The
focused suite covers the changed word-count parser, the end-to-end deterministic
price resolver, the canonical dataset adapter, prompt injection, profile
selection, artifact verification, and deploy contract. Full-suite execution is
delegated to CI before merge.
