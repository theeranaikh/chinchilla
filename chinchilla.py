from pathlib import Path

BASE_MODEL = "Qwen/Qwen2.5-1.5B"
DATA_DIR = Path("data")
ADAPTER_DIR = Path("outputs/lora-adapter")
MERGED_DIR = Path("outputs/merged")
GGUF_DIR = Path("outputs/gguf")
MAX_LEN = 768

SYSTEM_PROMPT = "คุณเป็นผู้ช่วยตอบคำถามจากบริบทที่ให้มา ตอบให้กระชับและถูกต้อง"
TEMPLATE = (
    "### System:\n{system}\n\n"
    "### Context:\n{context}\n\n"
    "### Question:\n{question}\n\n"
    "### Answer:\n"
)


def build_prompt(context: str, question: str) -> str:
    return TEMPLATE.format(system=SYSTEM_PROMPT, context=context, question=question)