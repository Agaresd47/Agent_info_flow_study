Status: dry_run
Timestamp: 20260502_180100
Condition: B0_guardrailed
Episodes: 2
Pairs: haiku_x_qwen, qwen_x_qwen
Seeds: [0, 1]
Judge model: gpt-5.4-mini

Cells:
- ep001_ct_mask_combine x haiku_x_qwen seed=0: verdict=spec_weak spec=0 worker=0 violations=[]
- ep001_ct_mask_combine x haiku_x_qwen seed=1: verdict=spec_weak spec=0 worker=0 violations=[]
- ep001_ct_mask_combine x qwen_x_qwen seed=0: verdict=spec_weak spec=0 worker=0 violations=[]
- ep001_ct_mask_combine x qwen_x_qwen seed=1: verdict=spec_weak spec=0 worker=0 violations=[]
- ep005_nnunet_dataset_json x haiku_x_qwen seed=0: verdict=spec_weak spec=0 worker=0 violations=[]
- ep005_nnunet_dataset_json x haiku_x_qwen seed=1: verdict=spec_weak spec=0 worker=0 violations=[]
- ep005_nnunet_dataset_json x qwen_x_qwen seed=0: verdict=spec_weak spec=0 worker=0 violations=[]
- ep005_nnunet_dataset_json x qwen_x_qwen seed=1: verdict=spec_weak spec=0 worker=0 violations=[]
