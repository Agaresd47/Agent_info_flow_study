# T2 Authoring Examples

Copy these files when creating a new T2 planner-worker episode.

- Put runner-visible facts in the episode YAML.
- Put gold constraints, expected pitfalls, decoys, and rubric rules in the paired judge YAML.
- Keep `planner_input.request_text` past user-intent clarification; ambiguity should be engineering-detail ambiguity.
- Do not add task-specific logic to `t2_matrix_runner.py`; if a new episode needs special scoring, express it in judge YAML.
