from .constants import LANGS


def compute_stats(rows):
    stats = {"total": len(rows)}
    for key in ("source", "risk", "language", "verdict"):
        counts = {}
        for r in rows:
            counts[r[key]] = counts.get(r[key], 0) + 1
        stats["by_" + key] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    model_rated = [r for r in rows if r["source"] == "model" and r["verdict"] != "unrated"]
    correct = sum(1 for r in model_rated if r["verdict"] == "correct")
    stats["rated"] = len(model_rated)
    stats["correct"] = correct
    stats["accuracy"] = correct / len(model_rated) * 100 if model_rated else None

    by_lang = []
    for lang in LANGS:
        sub = [r for r in model_rated if r["language"] == lang]
        if sub:
            ok = sum(1 for r in sub if r["verdict"] == "correct")
            by_lang.append((lang, len(sub), ok / len(sub) * 100))
    stats["accuracy_by_language"] = by_lang

    words = {}
    for r in rows:
        parts = r["command"].split()
        if parts:
            words[parts[0]] = words.get(parts[0], 0) + 1
    stats["top_commands"] = sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return stats


def bar(n, total, width=20):
    return "█" * round(n / total * width) if total else ""


def format_stats(stats):
    total = stats["total"]
    if total == 0:
        return ["ยังไม่มีข้อมูล"]
    lines = [f"จำนวนรายการทั้งหมด: {total}"]
    titles = (("by_source", "แยกตามที่มา"), ("by_risk", "แยกตามความเสี่ยง"),
              ("by_language", "แยกตามภาษาของคำขอ"), ("by_verdict", "แยกตามผลตรวจ"))
    for key, title in titles:
        lines.append(f"\n{title}")
        for name, n in stats[key]:
            lines.append(f"  {name:<9} {n:>4}  {bar(n, total)}")
    lines.append("\nความแม่นยำของคำสั่งที่โมเดลสร้าง (นับเฉพาะรายการที่ให้คะแนนแล้ว)")
    if stats["accuracy"] is None:
        lines.append("  ยังไม่มีรายการที่ให้คะแนน — ใช้เมนู 4 หรือ /rate ในแชท")
    else:
        lines.append(f"  ถูก {stats['correct']} จาก {stats['rated']} = {stats['accuracy']:.1f}%")
        for lang, n, pct in stats["accuracy_by_language"]:
            lines.append(f"    ภาษา {lang:<6} {n:>3} รายการ  ถูก {pct:.1f}%")
    lines.append("\nคำสั่งที่ใช้บ่อย (5 อันดับ)")
    for word, n in stats["top_commands"]:
        lines.append(f"  {word:<12} {n:>3}")
    return lines
