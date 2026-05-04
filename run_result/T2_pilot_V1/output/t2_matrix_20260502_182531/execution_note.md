Status: completed
Timestamp: 20260502_182531
Condition: B1_guardrailed
Episodes: 1
Pairs: haiku_x_qwen, qwen_x_qwen
Seeds: [0]
Judge model: gpt-5.4-mini

Cells:
- ep005_nnunet_dataset_json x haiku_x_qwen seed=0: verdict=spec_acceptable handoff=6 spec=5 worker=7 violations=['planner_v2_json_tail_missing_or_invalid', 'planner_json_tail_missing_or_invalid']
- ep005_nnunet_dataset_json x qwen_x_qwen seed=0: verdict=spec_weak handoff=4 spec=5 worker=5 violations=[]
