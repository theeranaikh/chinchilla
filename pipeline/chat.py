from pathlib import Path
import json

from .config import SYSTEM_PROMPT
from .inference import Generator, build_messages
from .shell import shell_flow
from .ui import PlainUI, RichUI


CHAT_HELP = """คำสั่งในหน้าต่างแชท
  (พิมพ์ข้อความเฉย ๆ)   คุยตามโหมดปัจจุบัน (chat = ถามตอบ, shell = สร้างและรันคำสั่ง)
  !<คำขอ>              สั่งเทอร์มินัลครั้งเดียวโดยไม่เปลี่ยนโหมด  เช่น  !ดูว่าโปรเซสไหนใช้พอร์ต 8080
  /sh <คำขอ>           เหมือน !
  /mode chat|shell     สลับโหมด
  /ctx <ข้อความ>        ตั้งบริบทให้โมเดลตอบจากบริบทนี้  (/ctx เฉย ๆ = ดู, /ctx clear = ล้าง)
  /reset               ล้างประวัติการคุย
  /cwd <โฟลเดอร์>       เปลี่ยนโฟลเดอร์ที่ใช้รันคำสั่ง
  /yes on|off          รันคำสั่งอ่านอย่างเดียว (ls, cat, grep ฯลฯ) โดยไม่ถาม
  /dry on|off          แสดงคำสั่งโดยไม่รัน
  /rate ok|bad         ให้คะแนนคำสั่งล่าสุดที่โมเดลสร้าง (ดูสถิติด้วย python3 command_log.py)
  /save [ไฟล์]          บันทึกบทสนทนาเป็น JSON
  /help   /exit  (หรือพิมพ์ exit / quit)
Ctrl-C ระหว่างตอบ = หยุดการตอบ,  Ctrl-C สองครั้งติดที่ช่องพิมพ์ หรือ Ctrl-D = ออก"""


def _trim_history(history, max_msgs, max_chars=6000):
    h = history[-max_msgs:]
    while len(h) > 2 and sum(len(m["content"]) for m in h) > max_chars:
        h = h[2:]
    return h


def _chat_turn(ui, gen, history, question, ctx, max_tokens, turns):
    user = build_messages(ctx, question)[1]["content"]
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + _trim_history(history, turns * 2) \
        + [{"role": "user", "content": user}]
    reply = ui.reply(gen.stream(msgs, max_tokens)).strip()
    if reply:
        history += [{"role": "user", "content": user}, {"role": "assistant", "content": reply}]


def cmd_chat(args):
    try:
        import readline
    except ImportError:
        pass
    ui = PlainUI()
    if not args.plain:
        try:
            ui = RichUI(art=not args.no_art)
        except ImportError:
            print("ไม่พบ rich — ใช้หน้าตาแบบธรรมดา (ติดตั้งด้วย: pip install rich)")

    st = {"mode": args.mode, "cwd": args.cwd, "yes": args.yes, "dry": args.dry_run, "ctx": "", "last_id": None}
    history = []
    ui.banner(f"backend: {args.backend} · โหมด: {st['mode']} · cwd: {Path(st['cwd']).resolve()}")
    with ui.loading():
        gen = Generator(args.backend, args.gguf, args.quant, args.max_tokens)

    def toggle(val, name):
        if val not in ("on", "off"):
            ui.error(f"ใช้: /{name} on|off")
            return None
        return val == "on"

    def slash(line):
        cmd, _, rest = line[1:].partition(" ")
        rest = rest.strip()
        cmd = cmd.lower()
        if cmd in ("exit", "quit"):
            return "exit"
        if cmd == "help":
            ui.help(CHAT_HELP)
        elif cmd == "reset":
            history.clear()
            ui.info("ล้างประวัติแล้ว")
        elif cmd == "mode":
            if rest in ("chat", "shell"):
                st["mode"] = rest
                ui.info(f"โหมด: {rest}")
            else:
                ui.error("ใช้: /mode chat|shell")
        elif cmd == "sh":
            if rest:
                st["last_id"] = shell_flow(gen, rest, ui, st["cwd"], args.timeout, st["yes"], st["dry"], not args.no_log)
            else:
                ui.error("ใช้: /sh <คำขอ>")
        elif cmd == "ctx":
            if rest == "clear":
                st["ctx"] = ""
                ui.info("ล้างบริบทแล้ว")
            elif rest:
                st["ctx"] = rest
                ui.info(f"ตั้งบริบทแล้ว ({len(rest)} ตัวอักษร)")
            else:
                ui.info(st["ctx"] or "(ไม่มีบริบท)")
        elif cmd == "cwd":
            p = Path(rest or ".").expanduser()
            if p.is_dir():
                st["cwd"] = str(p.resolve())
                ui.info(f"cwd: {st['cwd']}")
            else:
                ui.error("ไม่พบโฟลเดอร์นี้")
        elif cmd in ("yes", "dry"):
            v = toggle(rest, cmd)
            if v is not None:
                st[cmd] = v
                ui.info(f"{cmd}: {'on' if v else 'off'}")
        elif cmd == "rate":
            if not st["last_id"]:
                ui.error("ยังไม่มีคำสั่งที่ถูกบันทึก (ลองสั่งด้วย ! ก่อน)")
            elif rest not in ("ok", "bad"):
                ui.error("ใช้: /rate ok|bad  (ให้คะแนนคำสั่งล่าสุดที่โมเดลสร้าง)")
            else:
                try:
                    import command_log
                    done = command_log.set_verdict(st["last_id"], "correct" if rest == "ok" else "wrong")
                    ui.info(f"ให้คะแนน id {st['last_id']}: {'ถูก' if rest == 'ok' else 'ผิด'}" if done else "ไม่พบรายการ")
                except ImportError:
                    ui.error("ไม่พบ command_log.py")
                except Exception as e:
                    ui.error(f"ให้คะแนนไม่สำเร็จ: {e}")
        elif cmd == "save":
            out = Path(rest or "outputs/chat.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            ui.info(f"บันทึกแล้ว -> {out}")
        else:
            ui.error("ไม่รู้จักคำสั่งนี้ พิมพ์ /help")
        return None

    pressed = False
    while True:
        try:
            line = ui.prompt(st["mode"]).strip()
            pressed = False
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            if pressed:
                break
            pressed = True
            ui.info("(กด Ctrl-C อีกครั้งหรือพิมพ์ exit เพื่อออก)")
            continue
        if not line:
            continue
        if line.lower() in ("exit", "quit"):
            break
        try:
            if line.startswith("/"):
                if slash(line) == "exit":
                    break
            elif line.startswith("!") or st["mode"] == "shell":
                req = line[1:].strip() if line.startswith("!") else line
                if req:
                    st["last_id"] = shell_flow(gen, req, ui, st["cwd"], args.timeout, st["yes"], st["dry"], not args.no_log)
            else:
                _chat_turn(ui, gen, history, line, st["ctx"], args.max_tokens, args.turns)
        except KeyboardInterrupt:
            ui.info("[ยกเลิก]")
        except EOFError:
            print()
            break
    ui.bye()
