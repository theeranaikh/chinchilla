import json
import random
import re
import sys
import zlib

from .config import DATA_DIR, SHELL_SYSTEM, SYSTEM_PROMPT
from .inference import build_messages
from .safety import clean_command, is_blocked


def a_shell(r):
    nl = r.get("nl") or r.get("prompt") or r.get("instruction") or r.get("question")
    cmd = r.get("bash") or r.get("response") or r.get("output") or r.get("command") or r.get("answer")
    if not nl or not cmd:
        return None
    cmd = cmd.strip()
    if "```" in cmd:
        cmd = clean_command(cmd)
    if not cmd or "\n" in cmd or len(cmd) > 300 or is_blocked(cmd):
        return None
    return ("", nl, cmd)

SHELL_SLOTS = {
    "ext": ["py", "txt", "md", "json", "csv", "log", "jpg", "pdf", "png"],
    "file": ["notes.txt", "data.csv", "app.py", "main.py", "README.md", "config.json", "server.log", "report.pdf"],
    "dir": ["Documents", "Downloads", "Desktop", "projects", "src", "backup"],
    "port": ["3000", "5000", "8000", "8080", "5432"],
    "n": ["3", "5", "10", "20"],
    "word": ["error", "TODO", "main", "import", "debug", "feature"],
    "a": ["foo", "old", "localhost", "v1", "dev"],
    "b": ["bar", "new", "example", "v2", "prod"],
    "proc": ["python", "node", "nginx", "chrome"],
    "pkg": ["requests", "numpy", "pandas", "flask"],
    "host": ["google.com", "github.com", "example.com"],
    "url": ["https://example.com", "https://api.github.com"],
}

SHELL_TEMPLATES = [
    (["แสดงรายชื่อไฟล์ทั้งหมดในโฟลเดอร์นี้ รวมไฟล์ซ่อน", "ขอดูไฟล์ทั้งหมดในโฟลเดอร์ปัจจุบัน"],
     ["list all files in this directory including hidden ones", "show me everything in the current folder"], "ls -la"),
    (["ตอนนี้ฉันอยู่โฟลเดอร์ไหน", "แสดงพาธของโฟลเดอร์ปัจจุบัน"],
     ["where am I", "print the current working directory"], "pwd"),
    (["ค้นหาไฟล์ .{ext} ทั้งหมดในโฟลเดอร์นี้", "หาไฟล์นามสกุล {ext} ให้หน่อย"],
     ["find all .{ext} files here", "search for files with the {ext} extension"], 'find . -name "*.{ext}"'),
    (["ไฟล์ที่ใหญ่ที่สุด {n} อันดับแรกในโฟลเดอร์นี้", "หาไฟล์ที่กินพื้นที่มากที่สุด {n} ไฟล์"],
     ["show the {n} largest files here", "top {n} biggest files in this folder"],
     "find . -type f -exec du -h {{}} + | sort -rh | head -n {n}"),
    (["ค้นหาคำว่า {word} ในทุกไฟล์ของโฟลเดอร์นี้", "หาว่าคำว่า {word} อยู่ในไฟล์ไหนบ้าง"],
     ["search for {word} in all files here", "which files contain the word {word}"], 'grep -rn "{word}" .'),
    (["นับจำนวนบรรทัดของไฟล์ {file}", "{file} มีกี่บรรทัด"],
     ["count the lines in {file}", "how many lines does {file} have"], "wc -l {file}"),
    (["แสดง {n} บรรทัดแรกของ {file}", "ดูหัวไฟล์ {file} {n} บรรทัด"],
     ["show the first {n} lines of {file}", "print the top {n} lines of {file}"], "head -n {n} {file}"),
    (["แสดง {n} บรรทัดสุดท้ายของ {file}", "ดูท้ายไฟล์ {file} {n} บรรทัด"],
     ["show the last {n} lines of {file}", "print the final {n} lines of {file}"], "tail -n {n} {file}"),
    (["ติดตามไฟล์ {file} แบบเรียลไทม์", "ดู log {file} สด ๆ"],
     ["follow {file} in real time", "watch {file} as it grows"], "tail -f {file}"),
    (["แสดงเนื้อหาไฟล์ {file}", "เปิดอ่านไฟล์ {file}"],
     ["show the contents of {file}", "print {file}"], "cat {file}"),
    (["ดูพื้นที่ดิสก์ที่เหลือ", "ดิสก์เหลือเท่าไหร่"],
     ["show free disk space", "how much disk space is left"], "df -h"),
    (["โฟลเดอร์ {dir} ใหญ่เท่าไหร่", "ดูขนาดของโฟลเดอร์ {dir}"],
     ["how big is the {dir} folder", "show the size of {dir}"], "du -sh {dir}"),
    (["สร้างโฟลเดอร์ชื่อ {dir}", "สร้างไดเรกทอรี {dir}"],
     ["create a folder called {dir}", "make a directory named {dir}"], "mkdir -p {dir}"),
    (["สำรองไฟล์ {file} ไว้เป็น .bak", "คัดลอก {file} เป็นไฟล์สำรอง"],
     ["make a backup copy of {file}", "copy {file} to {file}.bak"], "cp {file} {file}.bak"),
    (["ย้ายไฟล์ {file} ไปไว้ในโฟลเดอร์ {dir}", "เอา {file} ไปใส่ใน {dir}"],
     ["move {file} into {dir}", "put {file} in the {dir} folder"], "mv {file} {dir}/"),
    (["สร้างไฟล์เปล่าชื่อ {file}", "สร้างไฟล์ใหม่ {file}"],
     ["create an empty file named {file}", "make a new file {file}"], "touch {file}"),
    (["ดูว่าโปรเซสไหนใช้พอร์ต {port}", "พอร์ต {port} ถูกใช้โดยอะไร"],
     ["what is using port {port}", "which process is listening on port {port}"], "lsof -i :{port}"),
    (["หยุดโปรเซสที่ใช้พอร์ต {port}", "ปิดโปรแกรมที่จับพอร์ต {port}"],
     ["kill the process on port {port}", "stop whatever is using port {port}"], "kill $(lsof -t -i :{port})"),
    (["ดูโปรเซส {proc} ที่กำลังทำงาน", "มี {proc} รันอยู่ไหม"],
     ["show running {proc} processes", "is {proc} running"], "ps aux | grep {proc}"),
    (["โปรเซสไหนกินซีพียูมากสุด", "ดู 10 โปรเซสที่ใช้ CPU สูงสุด"],
     ["which processes use the most CPU", "show top 10 processes by CPU"], "ps aux | sort -nrk 3 | head -n 10"),
    (["ดูสถานะ git", "git เปลี่ยนอะไรไปบ้าง"],
     ["show git status", "what has changed in git"], "git status"),
    (["ดูประวัติ commit ล่าสุด {n} รายการ", "แสดง git log {n} อันล่าสุดแบบสั้น"],
     ["show the last {n} commits", "short git log of the last {n} commits"], "git log --oneline -n {n}"),
    (["ดูรายชื่อ branch ทั้งหมด", "มี branch อะไรบ้าง"],
     ["list all git branches", "show branches"], "git branch -a"),
    (["สร้าง branch ใหม่ชื่อ {word} แล้วสลับไปใช้", "แตก branch {word} แล้วเปลี่ยนไปทำงานบนนั้น"],
     ["create and switch to a new branch called {word}", "make a branch {word} and check it out"],
     "git checkout -b {word}"),
    (["สร้าง virtual environment ของ python", "ทำ venv ใหม่ชื่อ .venv"],
     ["create a python virtual environment", "set up a new .venv"], "python3 -m venv .venv"),
    (["เปิดใช้งาน virtual environment", "activate .venv"],
     ["activate the virtual environment", "activate the .venv"], "source .venv/bin/activate"),
    (["ติดตั้งแพ็กเกจ {pkg} ด้วย pip", "pip install {pkg} ให้หน่อย"],
     ["install {pkg} with pip", "pip install {pkg}"], "pip install {pkg}"),
    (["ดูแพ็กเกจ python ที่ติดตั้งอยู่", "pip มีอะไรติดตั้งไว้บ้าง"],
     ["list installed python packages", "what's installed with pip"], "pip list"),
    (["ตรวจ HTTP header ของ {url}", "ดู response header ของเว็บ {url}"],
     ["show the HTTP headers of {url}", "fetch only the headers for {url}"], "curl -I {url}"),
    (["เช็กว่าเชื่อมต่อ {host} ได้ไหม", "ping {host} 4 ครั้ง"],
     ["ping {host} four times", "check if {host} is reachable"], "ping -c 4 {host}"),
    (["ดู IP ของเครื่องฉัน", "IP ในวงแลนของเครื่องนี้คืออะไร"],
     ["show my local IP address", "what is this machine's LAN IP"], "ipconfig getifaddr en0"),
    (["ดูเวอร์ชัน macOS", "ตอนนี้ใช้ macOS รุ่นไหน"],
     ["show the macOS version", "which macOS version is this"], "sw_vers"),
    (["ดูชื่อรุ่นของซีพียู", "เครื่องนี้ใช้ชิปอะไร"],
     ["show the CPU model", "what chip does this Mac have"], "sysctl -n machdep.cpu.brand_string"),
    (["ดูเวอร์ชัน python", "python เวอร์ชันอะไร"],
     ["show the python version", "which python version is installed"], "python3 --version"),
    (["แสดงวันที่ปัจจุบันในรูปแบบ ปี-เดือน-วัน", "วันนี้วันที่เท่าไหร่ ขอแบบ YYYY-MM-DD"],
     ["print today's date as YYYY-MM-DD", "show the date in ISO format"], 'date "+%Y-%m-%d"'),
    (["บีบอัดโฟลเดอร์ {dir} เป็นไฟล์ tar.gz", "แพ็กโฟลเดอร์ {dir} เป็น .tar.gz"],
     ["compress the {dir} folder into a tar.gz", "archive {dir} as a .tar.gz"], "tar -czf {dir}.tar.gz {dir}"),
    (["แตกไฟล์ {dir}.tar.gz", "คลายการบีบอัด {dir}.tar.gz"],
     ["extract {dir}.tar.gz", "untar {dir}.tar.gz"], "tar -xzf {dir}.tar.gz"),
    (["ทำให้ {file} รันได้", "เพิ่มสิทธิ์ execute ให้ {file}"],
     ["make {file} executable", "add execute permission to {file}"], "chmod +x {file}"),
    (["หาไฟล์ที่แก้ไขในช่วง {n} วันที่ผ่านมา", "ไฟล์ไหนถูกแก้ภายใน {n} วัน"],
     ["find files modified in the last {n} days", "which files changed in the past {n} days"],
     "find . -type f -mtime -{n}"),
    (["แทนที่คำว่า {a} เป็น {b} ในไฟล์ {file}", "เปลี่ยน {a} เป็น {b} ใน {file} ทั้งหมด"],
     ["replace {a} with {b} in {file}", "change every {a} to {b} in {file}"],
     "sed -i '' 's/{a}/{b}/g' {file}"),
    (["แสดงคอลัมน์แรกของไฟล์ {file}", "ดึงคอลัมน์แรกจาก {file}"],
     ["print the first column of {file}", "extract column one from {file}"], "awk '{{print $1}}' {file}"),
    (["นับบรรทัดที่ซ้ำกันใน {file} แสดง {n} อันดับแรก", "บรรทัดไหนใน {file} ซ้ำบ่อยสุด {n} อัน"],
     ["count duplicate lines in {file} and show the top {n}", "most frequent lines in {file}, top {n}"],
     "sort {file} | uniq -c | sort -rn | head -n {n}"),
    (["เปิดโฟลเดอร์นี้ใน Finder", "เปิดโฟลเดอร์ปัจจุบันด้วย Finder"],
     ["open this folder in Finder", "reveal the current directory in Finder"], "open ."),
    (["เปิดไฟล์ {file} ด้วยโปรแกรมเริ่มต้น", "เปิด {file}"],
     ["open {file} with the default app", "open {file}"], "open {file}"),
    (["คัดลอกเนื้อหาไฟล์ {file} ไปที่คลิปบอร์ด", "copy ข้อความใน {file} เข้า clipboard"],
     ["copy the contents of {file} to the clipboard", "put {file} on the clipboard"], "pbcopy < {file}"),
    (["ลบไฟล์ {file}", "เอาไฟล์ {file} ออก"],
     ["delete the file {file}", "remove {file}"], "rm {file}"),
    (["ดู container ของ docker ที่กำลังรัน", "docker รันอะไรอยู่"],
     ["list running docker containers", "what is docker running"], "docker ps"),
    (["ดูรายการแพ็กเกจที่ติดตั้งด้วย brew", "brew ติดตั้งอะไรไว้บ้าง"],
     ["list brew packages", "what is installed with homebrew"], "brew list"),
    (["ดูประวัติคำสั่งล่าสุด {n} คำสั่ง", "คำสั่งที่เพิ่งพิมพ์ {n} อันล่าสุด"],
     ["show my last {n} commands", "recent shell history, {n} entries"], "history | tail -n {n}"),
]


def gen_shell_synthetic(n, rng):
    out, seen, tries = [], set(), 0
    while len(out) < n and tries < n * 30:
        tries += 1
        th, en, cmd = rng.choice(SHELL_TEMPLATES)
        slot = {k: rng.choice(v) for k, v in SHELL_SLOTS.items()}
        if slot["a"] == slot["b"]:
            continue
        nl = rng.choice(th if rng.random() < 0.5 else en)
        try:
            nl, cmd = nl.format_map(slot), cmd.format_map(slot)
        except KeyError:
            continue
        if is_blocked(cmd) or (nl, cmd) in seen:
            continue
        seen.add((nl, cmd))
        out.append((nl, cmd))
    return out


def a_squad(r):
    a = r["answers"]["text"]
    return (r["context"], r["question"], a[0]) if a else None


def a_sciq(r):
    return (r.get("support") or "", r["question"], r["correct_answer"])


def a_dolly(r):
    if r.get("category") not in {"open_qa", "closed_qa", "general_qa"}:
        return None
    return (r.get("context") or "", r["instruction"], r["response"])


def a_instruct(r):
    q = r.get("instruction") or r.get("Instruction")
    ans = r.get("output") or r.get("Output") or r.get("response")
    ctx = r.get("input") or r.get("Input") or r.get("context") or ""
    return (ctx, q, ans) if q and ans else None


def a_belebele(r):
    n = int(r["correct_answer_num"])
    return (r["flores_passage"], r["question"], r[f"mc_answer{n}"])


def a_gsm8k(r):
    body, _, final = r["answer"].partition("####")
    body = re.sub(r"<<[^>]*>>", "", body).strip()
    return ("", r["question"], f"{body}\nThe answer is {final.strip()}.")


def a_translate(r):
    en, th = r["translation"]["en"].strip(), r["translation"]["th"].strip()
    if len(en) < 15 or len(th) < 8:
        return None
    if zlib.crc32(en.encode()) % 2:
        return ("", f"Translate to Thai: {en}", th)
    return ("", f"แปลเป็นภาษาอังกฤษ: {th}", en)

SOURCES = [

    dict(name="squad (EN, ctx QA)", path="rajpurkar/squad", split="train", fn=a_squad, role="train", w=0.4, min_ans=15),
    dict(name="iapp wiki QA (TH, ctx QA)", path="iapp/iapp_wiki_qa_squad", split="train", fn=a_squad, role="train", w=0.4, min_ans=15),
    dict(name="belebele (TH, reading)", path="facebook/belebele", config="tha_Thai", split="test", fn=a_belebele, role="train", w=0.25),
    dict(name="sciq (EN, science)", path="allenai/sciq", split="train", fn=a_sciq, role="train", w=0.3),

    dict(name="dolly (EN, general QA)", path="databricks/databricks-dolly-15k", split="train", fn=a_dolly, role="train", w=0.8, min_ans=40),
    dict(name="alpaca-cleaned (EN)", path="yahma/alpaca-cleaned", split="train", fn=a_instruct, role="train", w=0.8, min_ans=40),
    dict(name="dolly-th (TH, general QA)", path="Thaweewat/databricks-dolly-15k-th", split="train", fn=a_instruct, role="train", w=0.8, min_ans=30),
    dict(name="alpaca-th (TH, general)", path="Thaweewat/alpaca-cleaned-52k-th", split="train", fn=a_instruct, role="train", w=0.8, min_ans=30),
    dict(name="WangchanThaiInstruct (TH)", path="airesearch/WangchanThaiInstruct", split="train", fn=a_instruct, role="train", w=0.6, min_ans=30),

    dict(name="gsm8k (EN, math reasoning)", path="openai/gsm8k", config="main", split="train", fn=a_gsm8k, role="train", w=0.5),
    dict(name="opus-100 en-th (translate)", path="Helsinki-NLP/opus-100", config="en-th", split="train", fn=a_translate, role="train", w=0.6),

    dict(name="NL2SH-ALFA (shell)", path="westenfelder/NL2SH-ALFA", tries=[("train", "train"), (None, "train")],
         fn=a_shell, role="train", w=0.4, min_ans=2, system=SHELL_SYSTEM),
    dict(name="nl2bash (shell)", path="jiacheng-ye/nl2bash", tries=[(None, "train", "refs/convert/parquet")],
         fn=a_shell, role="train", w=0.4, min_ans=2, system=SHELL_SYSTEM),
    dict(name="bash-commands (shell)", path="aelhalili/bash-commands-dataset", tries=[(None, "train")],
         fn=a_shell, role="train", w=0.3, min_ans=2, system=SHELL_SYSTEM),

    dict(name="xquad.th (TH, eval)", path="google/xquad", config="xquad.th", split="validation", fn=a_squad, role="val", w=1.0, min_ans=0),
]


def cmd_prepare(args):
    from datasets import load_dataset
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    train, valid = [], []

    for s in SOURCES:
        if args.skip_shell and s.get("system") == SHELL_SYSTEM:
            continue
        ds, err = None, None
        for t in s.get("tries", [(s.get("config"), s.get("split"))]):
            cfg, split, rev = t[0], t[1], (t[2] if len(t) > 2 else None)
            try:
                ds = load_dataset(s["path"], cfg, split=split, revision=rev)
                break
            except Exception as e:
                err = e
        if ds is None:
            print(f"[skip] {s['name']}: {type(err).__name__}: {str(err)[:120]}")
            continue

        ds = ds.shuffle(seed=42)
        if s["role"] == "val":
            target, n_val = args.val_per_source, 0
        else:
            target = int(args.per_source * s["w"])
            n_val = max(10, target // 20)
        min_ans = s.get("min_ans", 0)
        got = []
        for r in ds:
            try:
                item = s["fn"](r)
            except Exception:
                continue
            if not item:
                continue
            ctx, q, ans = item
            if not q or not ans or not (min_ans <= len(ans) <= args.max_answer_chars):
                continue
            msgs = build_messages(ctx, q, ans, s.get("system", SYSTEM_PROMPT))
            text = tok.apply_chat_template(msgs, tokenize=False)
            if len(tok(text)["input_ids"]) > args.max_len:
                continue
            got.append({"messages": msgs})
            if len(got) >= target + n_val:
                break

        if s["role"] == "val":
            valid += got
        else:
            valid += got[:n_val]
            train += got[n_val:]
        print(f"{s['name']:32s} -> {len(got)} rows")

    if args.shell_synthetic and not args.skip_shell:
        pairs = gen_shell_synthetic(args.shell_synthetic, rng)
        rows = [{"messages": build_messages("", nl, cmd, SHELL_SYSTEM)} for nl, cmd in pairs]
        nv = max(10, len(rows) // 20)
        valid += rows[:nv]
        train += rows[nv:]
        print(f"{'shell synthetic (TH/EN, macOS)':32s} -> {len(rows)} rows")

    if not train:
        sys.exit("ไม่มีข้อมูล train เลย — ตรวจสอบอินเทอร์เน็ต/ชื่อ dataset")
    rng.shuffle(train)
    rng.shuffle(valid)
    for name, rows in (("train.jsonl", train), ("valid.jsonl", valid)):
        with (DATA_DIR / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train={len(train)} valid={len(valid)} -> {DATA_DIR}/")
    if len(valid) < args.min_valid_warn:
        print(f"warning: valid มี {len(valid)} แถว น้อยกว่า val_batches ที่ตั้งไว้อาจไม่พอ")
