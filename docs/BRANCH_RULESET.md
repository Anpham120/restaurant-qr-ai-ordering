# Branch Ruleset And Required Checks

This file records the branch protection settings the repository ruleset must
enforce. The GitHub Actions workflows already define these check names; the
repository settings must match this document so the checks become mandatory
gates.

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
- Release PR should be created from a workflow-managed release branch by
  `Promote Production`. The release branch is based on `main` and merges
  `develop` before opening the PR.
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
- `Promote Production` should use `RELEASE_BOT_TOKEN` instead of relying only on
  `GITHUB_TOKEN`, because release PR checks must be triggered as normal
  pull-request checks before `main` accepts the merge.
