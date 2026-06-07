# Branch Ruleset And Required Checks

This file records the branch protection settings required by issue #16. The
repository settings must match this document before issue #16 can be closed.

## develop

- Require pull request before merging.
- Require status checks before merging.
- Required checks:
  - `frontend-build`
  - `backend-test`
  - `docker-compose-config`
- Enable merge queue when the repository plan supports it.
- Allow auto-merge.
- Block force pushes.
- Block branch deletion.

## main

- Require pull request before merging.
- Release PR should be created from `develop` by `Promote Production`.
- Require status checks before merging.
- Required checks:
  - `frontend-build`
  - `backend-test`
  - `docker-compose-config`
- Enable merge queue when the repository plan supports it.
- Allow auto-merge.
- Block force pushes.
- Block branch deletion.

## Notes

- GitHub Actions workflows define the check names, but repository rulesets must
  be enabled in GitHub settings so these checks become mandatory gates.
- Human review is not required in the normal flow. People intervene only when
  checks fail, scope is wrong, or production risk is high.
