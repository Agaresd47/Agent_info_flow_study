# Task1 Authoring Examples

Use these files as copy-and-edit templates when asking another agent to author T1 assets.

- `example_read_only_task.yaml`
  - task-side fields for a `read_only` case
- `example_read_only_judge.yaml`
  - grading-only fields paired with the read-only task
- `example_cli_task.yaml`
  - task-side fields for a `cli_test` case
- `example_cli_judge.yaml`
  - grading/oracle fields paired with the CLI task
- `example_cli_fixture.yaml`
  - minimal workspace fixture for the CLI task
- `example_matrix_config.yaml`
  - minimal config for `t1_matrix_runner.py`
- `example_sandbox_config.yaml`
  - minimal config for `run_sandbox_eval.py`

Rule of thumb:

- task YAML: user request, grounded context, tool surface, missing slots
- judge YAML: preferred behavior, policy replies, oracle, score caps
- fixture YAML: synthetic workspace tree only
- config YAML: which tasks and runners to execute
