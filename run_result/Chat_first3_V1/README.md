# Chat_first3_V1

This bundle tracks the first three formal `read_only` T1 tasks after schema unification:

- `t1_cxr14_subset_extraction`
- `t1_heart_mask_merge_cleanup`
- `t1_totalseg_mask_quarantine`

Canonical input:

- `input/chat_first3_v1_config.yaml`

Canonical completed output:

- `output/t1_matrix_20260502_113147/`

Secondary output:

- `output/t1_matrix_20260502_113537/`
  - later dry-run validation bundle

Contents of each output run dir:

- `matrix.json`
- `records.jsonl`
- `execution_note.md`
- `prompt_previews/`

Useful commands:

1. Validate fixture/task wiring:
   `python scripts/task/task1/install_harness_validation_tasks.py --config configs/task1/chat_first3_assets.yaml --repo-root .`
2. Run the matrix:
   `python scripts/task/task1/t1_matrix_runner.py --config run_result/Chat_first3_V1/input/chat_first3_v1_config.yaml --out-dir run_result/Chat_first3_V1/output`
