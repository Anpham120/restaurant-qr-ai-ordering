# Approved pipeline selection

`pipeline_selection.json` is the reviewed production decision. It is not a
fresh health-check result.

To replace it:

1. Produce a clean `pipeline-selection-v3` raw artifact on the commit containing
   the proposed AI/prompt/menu/dataset changes, either from the `Research Pipeline
   Selection` workflow or a local clean run.
2. Require a valid winner and all safety hard gates.
3. Download the raw artifact and verify its SHA-256.
4. Copy the reviewed profile metrics, `model_policy`, winner, selection
   provenance, `research_commit_sha`, and `research_input_hash` into a
   new `pipeline-selection-v3` approved artifact.
5. Preserve deploy-required provenance fields such as `approved_at`,
   `source_run_id`, `source_artifact_name`, and `source_artifact_sha256`.
6. Prefer `python ai/evaluation/approve_pipeline_selection.py ...` so the
   approval step is repeatable and hashed.
6. Review and merge the artifact through the normal protected PR flow.

Staging and production recompute the hash. A changed AI runtime, scorer, KB,
dataset, requirements file, or menu dataset blocks deployment until the
research workflow is rerun and a new decision is approved.
