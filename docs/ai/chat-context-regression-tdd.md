# Chat context regression: suggested dishes remain factual evidence

## User journey

A guest receives two suggested dishes, then asks for the price of the second
dish. The assistant must resolve that dish from the current menu rather than
asking the guest to repeat its name.

## RED

`ChatStoreTests.DbStore_LedgerKeepsSuggestedItemsAvailableForFactualFollowUps`
was changed to assert that a `suggested` recommendation is not placed in the
backend's exclusion set. Before the fix it failed because `m_001` was present
in the set.

Command:

```powershell
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --filter FullyQualifiedName~ChatStoreTests.DbStore_LedgerKeepsSuggestedItemsAvailableForFactualFollowUps --no-restore
```

## GREEN

The ledger now treats only `rejected`, `accepted`, and `added_to_cart` as
recommendation exclusions. `suggested` remains in typed state and chat history,
which lets factual follow-ups resolve it while the Python recommendation policy
still prevents duplicate suggestions.

Validation:

```powershell
dotnet test backend/tests/RestaurantQrAiOrdering.Api.Tests/RestaurantQrAiOrdering.Api.Tests.csproj --no-restore
# Passed: 81

$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_price_for_second_suggested_dish_uses_second_item_in_order -v
# Passed: 1
```

The deployed staging smoke remains the final integration gate: it must answer
the price of the second suggested dish and preserve the winner from
`pipeline_selection.json` before merge or production deployment.

## Safe recovery when an LLM claim is unverified

### Failure mode

For an evidence-first recommendation, the model can return valid action cards
whose IDs and prices resolve against the live menu, alongside one unsupported
sentence.  The previous response gate correctly detected the unsupported
sentence, but then removed every action card as well.  A guest consequently
saw the generic "not enough verified evidence" fallback even though the menu
already contained safe, verified recommendations.

### RED

`AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim`
uses a deterministic test client that returns the real `m_009` card together
with the false claim that its price is 1 VND.  Before the change the response
contained no suggested actions, so the test failed.

```powershell
$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim -v
# Before fix: suggested action IDs were []
```

### GREEN

When at least one action card resolves to the current menu, the response gate
keeps those resolved cards, replaces the model prose with deterministic text
rendered from the live menu, and rebuilds claims from those cards.  It records
`MODEL_CLAIM_REPLACED_WITH_LIVE_MENU_EVIDENCE` for audit.  If no valid card
exists, the original fail-closed abstention remains unchanged.

```powershell
$env:PYTHONPATH='ai'
ai/.venv/Scripts/python.exe -m unittest `
  ai.tests.test_assistant_llm_first.AssistantLlmFirstTests.test_grounded_recommendation_survives_an_unverified_model_claim `
  ai.tests.test_fastpath_claim_grounding.FastPathClaimGroundingTests.test_claim_marked_unverified_cannot_pass_the_response_gate -v
# Passed: 2

ai/.venv/Scripts/python.exe -m unittest discover -s ai/tests -p "test_*.py"
# Passed: 393
```

This recovery is deliberately narrower than a fallback: it does not trust
model-generated facts, and it cannot introduce a dish, ID, or price that is
not present in the permitted menu evidence.  The subsequent staging smoke
checks the real Vietnamese recommendation journey before a merge is allowed.
