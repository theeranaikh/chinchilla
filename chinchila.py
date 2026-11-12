import torch

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model

model_id = "Qwen/Qwen2.5-1.5B"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)

cfg = LoraConfig(
    r= 16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "o_proj","gete_proj", "up_proj", "down_proj"],
    task_type="CAUSAL_LM"
    
)

model = get_peft_model(model, cfg)
model.print_trainable_parameters()
