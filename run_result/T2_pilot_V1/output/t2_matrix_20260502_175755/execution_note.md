Status: completed
Timestamp: 20260502_175755
Condition: B0_guardrailed
Episodes: 2
Pairs: haiku_x_qwen, qwen_x_qwen
Seeds: [0, 1]
Judge model: gpt-5.4-mini

Cells:
- ep001_ct_mask_combine x haiku_x_qwen seed=0: verdict=spec_weak spec=4 worker=4 violations=[]
- ep001_ct_mask_combine x haiku_x_qwen seed=1: verdict=spec_weak spec=5 worker=8 violations=[]
- ep001_ct_mask_combine x qwen_x_qwen seed=0: verdict=spec_weak spec=3 worker=4 violations=[]
- ep001_ct_mask_combine x qwen_x_qwen seed=1: verdict=spec_weak spec=4 worker=6 violations=[]
- ep006_symlink_dataset_split x haiku_x_qwen seed=0: verdict=spec_weak spec=4 worker=5 violations=['planner_json_tail_missing_or_invalid']
- ep006_symlink_dataset_split x haiku_x_qwen seed=1: verdict=spec_weak spec=4 worker=5 violations=[]
- ep006_symlink_dataset_split x qwen_x_qwen seed=0: verdict=spec_weak spec=4 worker=6 violations=['planner_json_tail_missing_or_invalid']
- ep006_symlink_dataset_split x qwen_x_qwen seed=1: verdict=spec_weak spec=3 worker=2 violations=[]
