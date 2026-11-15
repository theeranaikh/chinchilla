from datetime import datetime
from pathlib import Path
import csv
import os

from .constants import DATA_FILE, FIELDS, LANGS, MAX_TEXT, RISKS, SOURCES, VERDICTS, YES_NO
from .exceptions import DataFileError
from .helpers import classify_risk, detect_language


def ensure_file(path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(FIELDS)
    except OSError as e:
        raise DataFileError(f"สร้างไฟล์ {path} ไม่ได้: {e}") from e


def clean_row(rec):
    if None in rec:
        return None
    row = {k: (rec.get(k) or "").strip() for k in FIELDS}
    if not row["id"].isdigit() or not row["request"] or not row["command"]:
        return None
    checks = (("source", SOURCES), ("risk", RISKS), ("executed", YES_NO), ("verdict", VERDICTS), ("language", LANGS))
    for key, allowed in checks:
        if row[key] not in allowed:
            return None
    return row


def load_rows(path=None):
    path = Path(path or DATA_FILE)
    ensure_file(path)
    rows, bad = [], 0
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise DataFileError(f"หัวคอลัมน์ของ {path} ไม่ตรงกับรูปแบบที่โปรแกรมใช้")
            for rec in reader:
                row = clean_row(rec)
                if row is None:
                    bad += 1
                else:
                    rows.append(row)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise DataFileError(f"อ่านไฟล์ {path} ไม่สำเร็จ: {e}") from e
    return rows, bad


def save_rows(rows, path=None):
    path = Path(path or DATA_FILE)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    except OSError as e:
        raise DataFileError(f"บันทึกไฟล์ {path} ไม่สำเร็จ: {e}") from e


def append_row(row, path=None):
    path = Path(path or DATA_FILE)
    ensure_file(path)
    try:
        with path.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writerow(row)
    except OSError as e:
        raise DataFileError(f"เพิ่มข้อมูลลง {path} ไม่สำเร็จ: {e}") from e


def next_id(rows):
    biggest = 0
    for r in rows:
        if int(r["id"]) > biggest:
            biggest = int(r["id"])
    return biggest + 1


def make_row(rid, request, command, source, executed, verdict="unrated", note="", risk=None):
    request = " ".join(request.split())[:MAX_TEXT]
    command = " ".join(command.split())[:MAX_TEXT]
    row = {
        "id": str(rid),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language": detect_language(request),
        "request": request,
        "command": command,
        "source": source,
        "risk": risk or classify_risk(command),
        "executed": "yes" if executed else "no",
        "verdict": verdict,
        "note": " ".join(note.split())[:MAX_TEXT],
    }
    if clean_row(row) is None:
        raise ValueError("ข้อมูลรายการไม่ถูกต้อง (ว่างเปล่าหรือค่าไม่อยู่ในที่กำหนด)")
    return row


def append_model_entry(request, command, risk, executed, path=None):
    rows, _ = load_rows(path)
    row = make_row(next_id(rows), request, command, "model", executed, risk=risk if risk in RISKS else None)
    append_row(row, path)
    return int(row["id"])


def set_verdict(rid, verdict, path=None):
    if verdict not in VERDICTS:
        raise ValueError(f"verdict ต้องเป็นหนึ่งใน {VERDICTS}")
    rows, _ = load_rows(path)
    for r in rows:
        if int(r["id"]) == int(rid):
            r["verdict"] = verdict
            save_rows(rows, path)
            return True
    return False
