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
