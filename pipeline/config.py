from pathlib import Path


TRAIN_MODEL = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

DATA_DIR = Path("data")

ADAPTER_DIR = Path("outputs/lora-adapter")

MERGED_DIR = Path("outputs/merged")

GGUF_DIR = Path("outputs/gguf")

CONFIG_PATH = Path("outputs/lora_config.yaml")

VAL_HISTORY = Path("outputs/val_history.json")

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer accurately and concisely, in complete sentences. "
    "If a context is given, answer from it. Reply in the same language as the question. / "
    "คุณเป็นผู้ช่วยที่ตอบคำถามอย่างถูกต้องและกระชับเป็นประโยคที่สมบูรณ์ ถ้ามีบริบทให้ตอบจากบริบท "
    "และตอบเป็นภาษาเดียวกับคำถาม"
)

SHELL_SYSTEM = (
    "You are a command-line assistant for macOS (zsh). Convert the user's request (Thai or English) "
    "into exactly one shell command. Output only the command on a single line, with no explanation "
    "and no markdown. / คุณเป็นผู้ช่วยสร้างคำสั่งเทอร์มินัลสำหรับ macOS (zsh) "
    "แปลงคำขอของผู้ใช้เป็นคำสั่งเดียว ตอบเฉพาะคำสั่งบรรทัดเดียว ไม่ต้องอธิบาย"
)


CLI_DESCRIPTION = """
Pipeline fine-tune โมเดลถามตอบ ไทย + อังกฤษ (ทั่วไป + วิชาการ) สำหรับ Mac M1 RAM 8GB

ขั้นตอน:
  python pipeline.py prepare      # โหลด dataset หลายแหล่ง -> data/train.jsonl, data/valid.jsonl
  python pipeline.py train        # QLoRA ด้วย MLX (4-bit base) -> outputs/lora-adapter
  python pipeline.py merge        # เลือก checkpoint (best/last/เลขรอบ) แล้วรวมเข้า base fp16
  python pipeline.py test         # ลองถามตอบ (MLX) ก่อนแปลง
  python pipeline.py quantize     # HF -> GGUF -> Q4_K_M (llama.cpp)
  python pipeline.py test --backend gguf
  python pipeline.py shell "ลิสต์ไฟล์ที่ใหญ่ที่สุด 5 อันดับ"   # สั่งเทอร์มินัลด้วยภาษาธรรมดา (เว้นว่าง = โหมดโต้ตอบ)
  python pipeline.py chat                 # หน้าต่างแชท: คุยถามตอบ + !<คำขอ> สั่งเทอร์มินัล (/help ดูคำสั่ง)
  python pipeline.py docker

ติดตั้ง:
  pip install -U mlx-lm datasets transformers huggingface_hub rich
  pip install llama-cpp-python        # เฉพาะตอนทดสอบ GGUF
"""
