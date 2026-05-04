Status: completed
Timestamp: 20260502_181513
Condition: B1_guardrailed
Episodes: 1
Pairs: haiku_x_qwen, qwen_x_qwen
Seeds: [0]
Judge model: gpt-5.4-mini

Cells:
- ep005_nnunet_dataset_json x haiku_x_qwen seed=0: verdict=spec_weak spec=4 worker=4 violations=['planner_json_tail_missing_or_invalid']
- ep005_nnunet_dataset_json x qwen_x_qwen seed=0: verdict=spec_weak spec=4 worker=5 violations=[]
