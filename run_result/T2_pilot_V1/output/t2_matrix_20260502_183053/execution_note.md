Status: dry_run
Timestamp: 20260502_183053
Condition: B1_guardrailed
Rounds: 2
Episodes: 1
Pairs: haiku_x_qwen, qwen_x_qwen
Seeds: [0]
Judge model: gpt-5.4-mini

Cells:
- ep005_nnunet_dataset_json x haiku_x_qwen seed=0: verdict=spec_weak handoff=None spec=0 worker=0 violations=[]
- ep005_nnunet_dataset_json x qwen_x_qwen seed=0: verdict=spec_weak handoff=None spec=0 worker=0 violations=[]
