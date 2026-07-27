# AI timeout budget — TDD evidence

## Source and user journey

Derived from the approved production rollout: as a diner, I need the browser-facing
API to wait for the bounded AI request so a valid DeepSeek/Luna answer is not
discarded as a premature timeout.

## RED → GREEN

| Stage | Command | Result | What it proves |
| --- | --- | --- | --- |
| RED | `dotnet test backend/RestaurantQrAiOrdering.sln --configuration Release --no-restore --filter "FullyQualifiedName~DeploymentConfigurationTests.DockerCompose_AllowsPythonRequestBudgetToFinishBeforeBackendTimeout"` | Failed: the compose file did not expose a 50-second backend timeout. | The former 18-second API timeout was incompatible with the 45-second AI budget. |
| GREEN | Same focused command after the compose correction, plus `docker compose -f deploy/docker-compose.yml config --quiet` with required CI-safe variables. | Passed; compose validation passed. | The deployed defaults give the AI service 45 seconds and the API 50 seconds. |

The guard lives in `backend/tests/RestaurantQrAiOrdering.Api.Tests/DeploymentConfigurationTests.cs` and checks the compose defaults directly. It does not claim that an external model always responds before 45 seconds; it protects the internal timeout ordering used by deployment.

## Checkpoints

- `bb06fc3 test: reproduce AI timeout budget contract` — RED test update and observed failure.
- `cb6c3d8 fix(deploy): keep backend alive through AI budget` — minimal compose correction and GREEN evidence.

## Coverage and limits

The focused configuration test is a static deployment-contract test. Full backend regression and CI/security suites remain required before merge and deployment; their result is intentionally not claimed by this document.
