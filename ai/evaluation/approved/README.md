# Approved pipeline selection

`pipeline_selection.json` is the reviewed production decision. It is not a
fresh health-check result.

To replace it:

1. Run the `Research Pipeline Selection` workflow on the commit containing the
   proposed AI/prompt/menu/dataset changes.
2. Require a valid winner and all safety hard gates.
3. Download the raw artifact and verify its SHA-256.
4. Copy only the three profile metric objects and decision provenance into a
   new `pipeline-selection-approved-v2` artifact.
5. Set `research_input_hash` from
   `evaluation.research_inputs.compute_research_input_hash`.
6. Review and merge the artifact through the normal protected PR flow.

Staging and production recompute the hash. A changed AI runtime, scorer, KB,
dataset, requirements file, or menu dataset blocks deployment until the
research workflow is rerun and a new decision is approved.
