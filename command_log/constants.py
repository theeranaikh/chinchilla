from pathlib import Path


DATA_FILE = Path("data/command_log.csv")

REPORT_FILE = Path("reports/summary.txt")

FIELDS = ("id", "timestamp", "language", "request", "command", "source", "risk", "executed", "verdict", "note")

SOURCES = ("manual", "model")

RISKS = ("safe", "risky", "blocked")

VERDICTS = ("unrated", "correct", "wrong")

LANGS = ("th", "en", "mixed", "other")

YES_NO = ("yes", "no")

BLOCKED_WORDS = ("sudo", "mkfs", "shutdown", "reboot", "diskutil erase", "dd if=", ":(){")

RISKY_WORDS = ("rm ", "mv ", "kill", "chmod", "chown", "sed -i", ">")

PAGE_SIZE = 10

MAX_TEXT = 500
