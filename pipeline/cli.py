from .config import CLI_DESCRIPTION as __doc__
import argparse

from .chat import cmd_chat
from .config import BASE_MODEL, TRAIN_MODEL
from .data import cmd_prepare
from .inference import cmd_test
from .shell import cmd_shell
from .training import cmd_docker, cmd_merge, cmd_quantize, cmd_train


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("prepare")
    s.add_argument("--tokenizer", default=BASE_MODEL)
    s.add_argument("--per-source", type=int, default=600, help="จำนวนแถว train พื้นฐานต่อ dataset (คูณน้ำหนักแต่ละชุด)")
    s.add_argument("--val-per-source", type=int, default=200)
    s.add_argument("--max-len", type=int, default=768)
    s.add_argument("--max-answer-chars", type=int, default=700)
    s.add_argument("--min-valid-warn", type=int, default=100)
    s.add_argument("--shell-synthetic", type=int, default=400, help="จำนวนตัวอย่างคำสั่งเทอร์มินัลที่สร้างจาก template")
    s.add_argument("--skip-shell", action="store_true", help="ไม่ใส่ข้อมูลสั่งงานเทอร์มินัล")
    s.set_defaults(fn=cmd_prepare)

    s = sub.add_parser("train")
    s.add_argument("--train-model", default=TRAIN_MODEL)
    s.add_argument("--iters", type=int, default=500, help="1 step = batch*grad_accum ตัวอย่าง")
    s.add_argument("--batch-size", type=int, default=1)
    s.add_argument("--grad-accum", type=int, default=4)
    s.add_argument("--num-layers", type=int, default=16, help="layer ที่ใส่ LoRA (-1 = ทั้งหมด, กิน RAM มากขึ้น)")
    s.add_argument("--rank", type=int, default=16)
    s.add_argument("--lr", type=float, default=2e-5)
    s.add_argument("--max-len", type=int, default=768)
    s.add_argument("--val-batches", type=int, default=100, help="จำนวน batch ที่ใช้วัด val loss (มาก = นิ่งกว่าแต่ช้ากว่า)")
    s.add_argument("--eval-every", type=int, default=100, help="วัด val และบันทึก checkpoint ทุกกี่ step")
    s.add_argument("--resume", action="store_true")
    s.set_defaults(fn=cmd_train)

    s = sub.add_parser("merge")
    s.add_argument("--base", default=BASE_MODEL)
    s.add_argument("--checkpoint", default="best", help="best | last | เลข iter เช่น 300")
    s.set_defaults(fn=cmd_merge)

    s = sub.add_parser("quantize")
    s.add_argument("--llama-cpp", default="./llama.cpp")
    s.add_argument("--quant", default="Q4_K_M")
    s.set_defaults(fn=cmd_quantize)

    s = sub.add_parser("test")
    s.add_argument("--backend", choices=["mlx", "gguf"], default="mlx")
    s.add_argument("--gguf", default=None)
    s.add_argument("--quant", default="Q4_K_M")
    s.add_argument("--context", default="")
    s.add_argument("--question", default="เมืองหลวงของประเทศไทยคืออะไร")
    s.add_argument("--max-tokens", type=int, default=300)
    s.set_defaults(fn=cmd_test)

    s = sub.add_parser("shell", help="สั่งเทอร์มินัลด้วยภาษาธรรมดา")
    s.add_argument("request", nargs="*", help="คำขอ (เว้นว่าง = โหมดโต้ตอบ)")
    s.add_argument("--backend", choices=["mlx", "gguf"], default="mlx")
    s.add_argument("--gguf", default=None)
    s.add_argument("--quant", default="Q4_K_M")
    s.add_argument("--cwd", default=".", help="โฟลเดอร์ที่ใช้รันคำสั่ง")
    s.add_argument("--timeout", type=int, default=30)
    s.add_argument("--no-log", action="store_true", help="ไม่บันทึกคำสั่งลง data/command_log.csv")
    s.add_argument("--dry-run", action="store_true", help="แสดงคำสั่งที่โมเดลสร้าง แต่ไม่รัน")
    s.add_argument("--yes", action="store_true", help="รันคำสั่งอ่านอย่างเดียว (ls, cat, grep ฯลฯ) โดยไม่ถาม; คำสั่งอื่นยังถามเสมอ")
    s.set_defaults(fn=cmd_shell)

    s = sub.add_parser("chat", help="หน้าต่างแชทบนเทอร์มินัล (คุย + สั่งคำสั่ง)")
    s.add_argument("--backend", choices=["mlx", "gguf"], default="mlx")
    s.add_argument("--gguf", default=None)
    s.add_argument("--quant", default="Q4_K_M")
    s.add_argument("--mode", choices=["chat", "shell"], default="chat")
    s.add_argument("--cwd", default=".")
    s.add_argument("--timeout", type=int, default=30)
    s.add_argument("--max-tokens", type=int, default=400)
    s.add_argument("--turns", type=int, default=4, help="จำนวนรอบล่าสุดที่จำไว้ในแชท")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--yes", action="store_true", help="รันคำสั่งอ่านอย่างเดียวโดยไม่ถาม")
    s.add_argument("--no-log", action="store_true", help="ไม่บันทึกคำสั่งลง data/command_log.csv")
    s.add_argument("--plain", action="store_true", help="ใช้หน้าตาตัวอักษรธรรมดา (ไม่ใช้ rich)")
    s.add_argument("--no-art", action="store_true", help="ไม่แสดงศิลปะ ASCII ตรงหัว")
    s.set_defaults(fn=cmd_chat)

    s = sub.add_parser("docker")
    s.add_argument("--quant", default="Q4_K_M")
    s.set_defaults(fn=cmd_docker)

    args = p.parse_args()
    args.fn(args)
