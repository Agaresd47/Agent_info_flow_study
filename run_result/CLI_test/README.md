# CLI_test

This bundle tracks the non-dry-run CLI sandbox result for:

- `t1_cli_original_case_reformat_nn_unet_guarded`

Canonical input:

- `input/cli_first1_v1_config.yaml`

Canonical output:

- `output/CLI_first1_V1.json`

Current status:

- `haiku_4_5`: `oracle=True`
- This V1 bundle is intentionally pinned to the passing runner so the saved result is directly usable.

Useful command:

`python scripts/task/task1/run_sandbox_eval.py --config run_result/CLI_test/input/cli_first1_v1_config.yaml --output run_result/CLI_test/output/CLI_first1_V1.json`

Multi-model comparison command:

`python scripts/task/task1/run_sandbox_eval.py --config run_result/CLI_test/input/cli_first1_v1_all4_config.yaml --output run_result/CLI_test/output/CLI_first1_V1_all4.json`
