from .constants import BLOCKED_WORDS, RISKY_WORDS


def detect_language(text):
    thai = 0
    letters = 0
    for ch in text:
        if ch.isalpha():
            letters += 1
            if "\u0e00" <= ch <= "\u0e7f":
                thai += 1
    if letters == 0:
        return "other"
    ratio = thai / letters
    if ratio >= 0.3:
        return "th"
    if thai > 0:
        return "mixed"
    return "en"


def classify_risk(command):
    c = command.lower()
    for word in BLOCKED_WORDS:
        if word in c:
            return "blocked"
    for word in RISKY_WORDS:
        if word in c:
            return "risky"
    return "safe"


def clip(text, width):
    return text if len(text) <= width else text[: width - 1] + "…"
