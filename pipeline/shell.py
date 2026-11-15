from pathlib import Path
import subprocess

from .config import SHELL_SYSTEM
from .inference import Generator, build_messages
from .safety import clean_command, is_blocked, is_readonly, is_risky
from .ui import PlainUI


def run_command(cmd, cwd, timeout):
    shell = "/bin/zsh" if Path("/bin/zsh").exists() else "/bin/bash"
    try:
        r = subprocess.run(cmd, shell=True, executable=shell, cwd=cwd,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"หมดเวลา ({timeout}s) — หยุดคำสั่งแล้ว", None
    return (r.stdout + r.stderr).rstrip(), r.returncode


def _log_entry(req, cmd, risk, executed):
    try:
        import command_log
        return command_log.append_model_entry(req, cmd, risk, executed)
    except ImportError:
        return None
    except Exception as e:
        print(f"(บันทึก log ไม่สำเร็จ: {e})")
        return None


def shell_flow(gen, req, ui, cwd=".", timeout=30, yes=False, dry_run=False, log=True):
    with ui.thinking():
        raw = gen(build_messages("", req, None, SHELL_SYSTEM), max_tokens=120)
    cmd = clean_command(raw)
    if not cmd:
        ui.error("โมเดลไม่ได้ให้คำสั่งกลับมา")
        return
    ui.command(cmd)
    risk = "blocked" if is_blocked(cmd) else ("risky" if is_risky(cmd) else "safe")

    def record(executed):
        return _log_entry(req, cmd, risk, executed) if log else None

    if risk == "blocked":
        ui.error("ปฏิเสธ: คำสั่งนี้อยู่ในรายการอันตราย จะไม่ถูกรัน")
        return record(False)
    if dry_run:
        return record(False)
    if not (yes and is_readonly(cmd)):
        warn = "⚠ คำสั่งนี้อาจแก้ไข/ลบข้อมูล " if risk == "risky" else ""
        if not ui.confirm(warn):
            return record(False)
    text, code = run_command(cmd, cwd, timeout)
    ui.output(text, code)
    return record(True)


def cmd_shell(args):
    ui = PlainUI()
    gen = Generator(args.backend, args.gguf, args.quant)
    if args.request:
        shell_flow(gen, " ".join(args.request), ui, args.cwd, args.timeout, args.yes, args.dry_run, not args.no_log)
        return
    print("โหมดโต้ตอบ — พิมพ์คำขอเป็นภาษาไทยหรืออังกฤษ (exit เพื่อออก)  ลองใช้ `chat` ถ้าอยากคุยด้วย")
    while True:
        try:
            req = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if req.lower() in {"exit", "quit"}:
            break
        if req:
            shell_flow(gen, req, ui, args.cwd, args.timeout, args.yes, args.dry_run, not args.no_log)
