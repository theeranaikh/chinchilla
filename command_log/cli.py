from datetime import datetime
from pathlib import Path
import argparse
import sys

from .constants import DATA_FILE, MAX_TEXT, PAGE_SIZE, REPORT_FILE, SOURCES, VERDICTS
from .exceptions import Cancelled, DataFileError
from .helpers import clip
from .stats import compute_stats, format_stats
from .storage import append_row, load_rows, make_row, next_id, save_rows


def read_line(prompt):
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        raise Cancelled from None


def ask_text(prompt, allow_empty=False):
    while True:
        s = read_line(prompt)
        if not s and not allow_empty:
            print("  ! ห้ามเว้นว่าง")
        elif len(s) > MAX_TEXT:
            print(f"  ! ยาวเกิน {MAX_TEXT} ตัวอักษร (พิมพ์มา {len(s)})")
        else:
            return s


def ask_int(prompt, low, high):
    while True:
        s = read_line(prompt)
        try:
            n = int(s)
        except ValueError:
            print("  ! กรุณากรอกเป็นตัวเลขจำนวนเต็ม")
            continue
        if low <= n <= high:
            return n
        print(f"  ! ต้องอยู่ระหว่าง {low}-{high}")


def ask_choice(prompt, options):
    for i, opt in enumerate(options, start=1):
        print(f"   {i}. {opt}")
    while True:
        s = read_line(prompt).lower()
        if s in options:
            return s
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1]
        print(f"  ! เลือก 1-{len(options)} หรือพิมพ์ชื่อตัวเลือก")


def ask_yes_no(prompt):
    while True:
        s = read_line(prompt + " [y/n]: ").lower()
        if s in ("y", "yes", "ใช่"):
            return True
        if s in ("n", "no", "ไม่"):
            return False
        print("  ! ตอบ y หรือ n")


def print_table(rows):
    print(f"{'id':>4}  {'วันเวลา':<19}  {'ที่มา':<6} {'เสี่ยง':<7} {'ผล':<8}  คำขอ  =>  คำสั่ง")
    print("-" * 100)
    for r in rows:
        print(f"{r['id']:>4}  {r['timestamp']:<19}  {r['source']:<6} {r['risk']:<7} {r['verdict']:<8}  "
              f"{clip(r['request'], 28)}  =>  {clip(r['command'], 38)}")


def show_rows(rows):
    if not rows:
        print("(ไม่มีรายการ)")
        return
    total_pages = (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE
    page = 0
    while True:
        start = page * PAGE_SIZE
        print_table(rows[start:start + PAGE_SIZE])
        print(f"หน้า {page + 1}/{total_pages}  (ทั้งหมด {len(rows)} รายการ)")
        if total_pages == 1:
            return
        cmd = read_line("[n] ถัดไป  [p] ก่อนหน้า  [q] กลับเมนู: ").lower()
        if cmd in ("n", "next"):
            if page < total_pages - 1:
                page += 1
            else:
                print("  อยู่หน้าสุดท้ายแล้ว")
        elif cmd in ("p", "prev"):
            if page > 0:
                page -= 1
            else:
                print("  อยู่หน้าแรกแล้ว")
        elif cmd in ("q", "quit", ""):
            return
        else:
            print("  ! พิมพ์ n, p หรือ q")


def action_add(path):
    rows, _ = load_rows(path)
    print("เพิ่มรายการใหม่ — ที่มาของคำสั่ง:")
    source = ask_choice("เลือก: ", SOURCES)
    request = ask_text("คำขอ/สิ่งที่ต้องการทำ (ไทยหรืออังกฤษ): ")
    command = ask_text("คำสั่งเทอร์มินัล: ")
    executed = ask_yes_no("เคยรันคำสั่งนี้แล้วหรือยัง")
    verdict = "unrated"
    if source == "model":
        print("คำสั่งนี้ถูกต้องไหม?")
        verdict = ask_choice("เลือก: ", VERDICTS)
    note = ask_text("หมายเหตุ (เว้นว่างได้): ", allow_empty=True)
    row = make_row(next_id(rows), request, command, source, executed, verdict, note)
    append_row(row, path)
    msg = f"บันทึกแล้ว: id {row['id']}, ภาษา {row['language']}, ความเสี่ยง {row['risk']}"
    print(msg)
    if row["risk"] == "blocked":
        print("  ⚠ คำสั่งนี้ถูกจัดเป็นอันตราย — บันทึกไว้เพื่ออ้างอิงเท่านั้น อย่ารันโดยไม่เข้าใจ")


def action_search(path):
    rows, _ = load_rows(path)
    kw = ask_text("คำค้น (ค้นในคำขอและคำสั่ง): ").lower()
    found = [r for r in rows if kw in r["request"].lower() or kw in r["command"].lower()]
    print(f"พบ {len(found)} รายการ")
    show_rows(found)


def find_by_id(rows, rid):
    for r in rows:
        if int(r["id"]) == rid:
            return r
    return None


def action_rate(path):
    rows, _ = load_rows(path)
    if not rows:
        print("(ไม่มีรายการ)")
        return
    ids = [int(r["id"]) for r in rows]
    rid = ask_int(f"id ที่ต้องการให้คะแนน ({min(ids)}-{max(ids)}): ", min(ids), max(ids))
    row = find_by_id(rows, rid)
    if row is None:
        print(f"  ! ไม่พบ id {rid}")
        return
    print(f"คำขอ: {row['request']}\nคำสั่ง: {row['command']}\nผลปัจจุบัน: {row['verdict']}")
    row["verdict"] = ask_choice("ผลใหม่: ", VERDICTS)
    save_rows(rows, path)
    print("อัปเดตแล้ว")


def action_delete(path):
    rows, _ = load_rows(path)
    if not rows:
        print("(ไม่มีรายการ)")
        return
    rid = ask_int("id ที่ต้องการลบ: ", 1, 10**9)
    row = find_by_id(rows, rid)
    if row is None:
        print(f"  ! ไม่พบ id {rid}")
        return
    print(f"จะลบ: [{row['id']}] {row['request']} => {row['command']}")
    if ask_yes_no("ยืนยันการลบ"):
        rows.remove(row)
        save_rows(rows, path)
        print("ลบแล้ว")
    else:
        print("ยกเลิก")


def action_stats(path):
    rows, _ = load_rows(path)
    print("\n".join(format_stats(compute_stats(rows))))


def action_report(path):
    rows, _ = load_rows(path)
    lines = ["Terminal Command Journal — รายงานสรุป",
             f"สร้างเมื่อ {datetime.now():%Y-%m-%d %H:%M:%S}  จากไฟล์ {path}", "=" * 60]
    lines += format_stats(compute_stats(rows))
    try:
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as e:
        raise DataFileError(f"เขียนรายงานไม่สำเร็จ: {e}") from e
    print(f"ส่งออกรายงานแล้ว -> {REPORT_FILE}")

MENU = (
    ("1", "เพิ่มรายการ", action_add),
    ("2", "ดูรายการทั้งหมด", lambda p: show_rows(load_rows(p)[0])),
    ("3", "ค้นหา", action_search),
    ("4", "ให้คะแนนคำสั่ง (ถูก/ผิด)", action_rate),
    ("5", "ลบรายการ", action_delete),
    ("6", "สรุปสถิติ", action_stats),
    ("7", "ส่งออกรายงาน .txt", action_report),
)


def main():
    parser = argparse.ArgumentParser(description="Terminal Command Journal")
    parser.add_argument("--file", default=str(DATA_FILE), help="ไฟล์ CSV ที่ใช้เก็บข้อมูล")
    path = Path(parser.parse_args().file)

    try:
        rows, bad = load_rows(path)
    except DataFileError as e:
        sys.exit(f"เริ่มโปรแกรมไม่ได้: {e}")
    print("=" * 60)
    print(" Terminal Command Journal — สมุดบันทึกคำสั่งเทอร์มินัล")
    print(f" ไฟล์ข้อมูล: {path}  ({len(rows)} รายการ)")
    if bad:
        print(f" ⚠ ข้ามแถวที่ข้อมูลไม่ถูกต้อง {bad} แถว (ไม่ได้ลบออกจากไฟล์)")
    print("=" * 60)

    actions = {key: fn for key, _, fn in MENU}
    while True:
        print()
        for key, title, _ in MENU:
            print(f"  {key}. {title}")
        print("  0. ออก")
        try:
            choice = read_line("เลือกเมนู: ")
        except Cancelled:
            break
        if choice == "0":
            break
        if choice not in actions:
            print("  ! ไม่มีเมนูนี้ เลือก 0-7")
            continue
        try:
            actions[choice](path)
        except Cancelled:
            print("(ยกเลิก กลับเมนู)")
        except (DataFileError, ValueError) as e:
            print(f"  ! {e}")
        except Exception as e:
            print(f"  ! เกิดข้อผิดพลาดที่ไม่คาดคิด: {type(e).__name__}: {e}")
    print("ขอบคุณที่ใช้งาน")
