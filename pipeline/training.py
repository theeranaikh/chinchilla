from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

from .config import ADAPTER_DIR, CONFIG_PATH, DATA_DIR, GGUF_DIR, MERGED_DIR, VAL_HISTORY


VAL_RES = [
    re.compile(r"^\s*(\d+)\s+val\s+([0-9.]+)", re.I),
    re.compile(r"Iter\s+(\d+):\s*Val loss\s+([0-9.]+)", re.I),
]

TRAIN_LOG = Path("outputs/train.log")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def cmd_train(args):
    if not (DATA_DIR / "train.jsonl").exists():
        sys.exit("ยังไม่มีข้อมูล รัน: python pipeline.py prepare")
    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    cfg = f"""model: {args.train_model}
train: true
data: {DATA_DIR}
fine_tune_type: lora
adapter_path: {ADAPTER_DIR}
num_layers: {args.num_layers}
batch_size: {args.batch_size}
grad_accumulation_steps: {args.grad_accum}
iters: {args.iters}
learning_rate: {format(args.lr, "f")}
max_seq_length: {args.max_len}
grad_checkpoint: true
mask_prompt: true
val_batches: {args.val_batches}
steps_per_report: 10
steps_per_eval: {args.eval_every}
save_every: {args.eval_every}
seed: 0
lora_parameters:
  keys: ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj",
         "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]
  rank: {args.rank}
  scale: 20.0
  dropout: 0.05
"""
    CONFIG_PATH.write_text(cfg)
    print(f"config -> {CONFIG_PATH}")
    cmd = [sys.executable, "-m", "mlx_lm", "lora", "-c", str(CONFIG_PATH)]
    if args.resume and (ADAPTER_DIR / "adapters.safetensors").exists():
        cmd += ["--resume-adapter-file", str(ADAPTER_DIR / "adapters.safetensors")]

    history = {}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    with TRAIN_LOG.open("w", encoding="utf-8") as log:
        for line in proc.stdout:
            clean = ANSI_RE.sub("", line)
            log.write(clean)
            for rx in VAL_RES:
                m = rx.search(clean)
                if m:
                    history[int(m.group(1))] = float(m.group(2))
                    VAL_HISTORY.write_text(json.dumps(history))
                    break
            if "█" not in line:
                print(line, end="", flush=True)
    if proc.wait() != 0:
        sys.exit("mlx_lm lora ล้มเหลว")
    print(f"saved adapter -> {ADAPTER_DIR}")
    if history:
        usable = {k: v for k, v in history.items() if (ADAPTER_DIR / f"{k:07d}_adapters.safetensors").exists()}
        if usable:
            best = min(usable, key=usable.get)
            print(f"best val loss {usable[best]:.3f} ที่ iter {best} -> merge ด้วย: python pipeline.py merge --checkpoint best")
    else:
        print(f"อ่าน val loss ไม่ได้ — ดู {TRAIN_LOG} แล้วใช้ --checkpoint <เลข iter> ตอน merge")


def _select_checkpoint(choice):
    final = ADAPTER_DIR / "adapters.safetensors"
    backup = ADAPTER_DIR / "adapters_last.safetensors"
    if final.exists() and not backup.exists():
        shutil.copy(final, backup)
    if choice == "last":
        if backup.exists():
            shutil.copy(backup, final)
        return "last"
    if choice == "best":
        if not VAL_HISTORY.exists():
            print("ไม่พบ val_history.json -> ใช้รอบสุดท้าย (หรือระบุ --checkpoint <เลข iter>)")
            return "last"
        hist = {int(k): v for k, v in json.loads(VAL_HISTORY.read_text()).items()}
        hist = {k: v for k, v in hist.items() if (ADAPTER_DIR / f"{k:07d}_adapters.safetensors").exists()}
        if not hist:
            return "last"
        choice = str(min(hist, key=hist.get))
    ck = ADAPTER_DIR / f"{int(choice):07d}_adapters.safetensors"
    if not ck.exists():
        sys.exit(f"ไม่พบ {ck}")
    shutil.copy(ck, final)
    return f"iter {int(choice)}"


def cmd_merge(args):
    used = _select_checkpoint(args.checkpoint)
    print(f"ใช้ adapter: {used}")
    subprocess.run(
        [sys.executable, "-m", "mlx_lm", "fuse",
         "--model", args.base,
         "--adapter-path", str(ADAPTER_DIR),
         "--save-path", str(MERGED_DIR)],
        check=True,
    )
    print(f"merged model -> {MERGED_DIR}")


def cmd_quantize(args):
    llama = Path(args.llama_cpp)
    convert = llama / "convert_hf_to_gguf.py"
    quant_bin = llama / "build" / "bin" / "llama-quantize"
    if not convert.exists() or not quant_bin.exists():
        sys.exit(
            "ไม่พบ llama.cpp ที่ build แล้ว:\n"
            "  git clone https://github.com/ggerganov/llama.cpp\n"
            "  cd llama.cpp && cmake -B build && cmake --build build --config Release -j\n"
            "  pip install -r requirements.txt"
        )

    GGUF_DIR.mkdir(parents=True, exist_ok=True)
    f16 = GGUF_DIR / "model-f16.gguf"
    out = GGUF_DIR / f"model-{args.quant}.gguf"

    subprocess.run(
        [sys.executable, str(convert), str(MERGED_DIR),
         "--outfile", str(f16), "--outtype", "f16"],
        check=True,
    )
    subprocess.run([str(quant_bin), str(f16), str(out), args.quant], check=True)
    f16.unlink(missing_ok=True)
    print(f"quantized -> {out}")


def cmd_docker(args):
    dockerfile = f"""FROM ghcr.io/ggml-org/llama.cpp:server
COPY outputs/gguf/model-{args.quant}.gguf /models/model.gguf
EXPOSE 8080
ENTRYPOINT ["/app/llama-server", "-m", "/models/model.gguf", "--host", "0.0.0.0", "--port", "8080", "-c", "2048", "--jinja"]
"""
    Path("Dockerfile").write_text(dockerfile)
    print("wrote Dockerfile")
    print("build/run:")
    print("  docker build -t qa-llm .")
    print("  docker run -p 8080:8080 qa-llm")
    print('  curl localhost:8080/v1/chat/completions -H "Content-Type: application/json" \\')
    print("    -d '{\"messages\":[{\"role\":\"user\",\"content\":\"สวัสดี\"}]}'")
    print("แล้ว deploy ขึ้น DigitalOcean Droplet หรือ Azure Container Apps")
