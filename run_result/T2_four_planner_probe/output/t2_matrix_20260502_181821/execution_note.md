Status: completed
Timestamp: 20260502_181821
Condition: B0_guardrailed
Episodes: 1
Pairs: haiku_x_qwen, qwen_x_qwen, glm_x_qwen, kimi_x_qwen
Seeds: [0]
Judge model: gpt-5.4-mini

Cells:
- ep005_nnunet_dataset_json x haiku_x_qwen seed=0: verdict=spec_weak spec=4 worker=7 violations=[]
- ep005_nnunet_dataset_json x qwen_x_qwen seed=0: verdict=spec_weak spec=4 worker=4 violations=[]
- ep005_nnunet_dataset_json x glm_x_qwen seed=0: verdict=spec_weak spec=3 worker=5 violations=[]
- ep005_nnunet_dataset_json x kimi_x_qwen seed=0: verdict=spec_weak spec=2 worker=7 violations=[]
