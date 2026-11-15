import re
import shlex


BLOCKED = [
    r"\bsudo\b",
    r"\bmkfs",
    r"\bdiskutil\s+(erase|partition|secure|zero)",
    r"\bdd\b.*\bof=/dev/",
    r":\(\)\s*\{",
    r"\b(shutdown|reboot|halt)\b",
    r"(curl|wget)\b.*\|\s*(sudo\s+)?(ba|z)?sh\b",
    r">\s*/dev/(sd|disk|nvme)",
    r"\bchmod\s+(-R\s+)?[0-7]*777\s+/",
    r"\brm\b(\s+-\S+)*\s+(/|~|\$HOME|/\*|\*|\.|\.\.)(\s|$)",
    r"\brm\b(\s+-\S+)*\s+/(usr|etc|bin|sbin|var|System|Library|Users|Applications|opt)\b",
]

RISKY = [
    r"\brm\b", r"\bmv\b", r"\bkill(all)?\b", r"\bchown\b", r"\bchmod\s+-R",
    r"\bsed\s+-i", r"\bgit\s+(reset\s+--hard|clean|push\b.*(-f\b|--force))",
    r"\b(pip|brew|npm)\s+uninstall\b", r"(^|[^>])>[^>&]",
]

READ_ONLY = {
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "df", "du", "ps", "date", "which",
    "whoami", "uname", "sw_vers", "sysctl", "sort", "uniq", "lsof", "find", "git", "python3", "python",
}


def is_blocked(cmd):
    return any(re.search(p, cmd) for p in BLOCKED)


def is_risky(cmd):
    return any(re.search(p, cmd) for p in RISKY)


def is_readonly(cmd):
    if re.search(r"[;&`><]|\$\(", cmd):
        return False
    for seg in cmd.split("|"):
        try:
            w = shlex.split(seg)
        except ValueError:
            return False
        if not w or w[0] not in READ_ONLY:
            return False
        if w[0] == "git" and not (len(w) > 1 and w[1] in {"status", "log", "diff", "branch", "show"}):
            return False
        if w[0] == "find" and any(x in ("-delete", "-exec", "-execdir", "-ok") for x in w):
            return False
        if w[0] in ("python3", "python") and w[1:] != ["--version"]:
            return False
        if w[0] == "tail" and "-f" in w:
            return False
    return True


def clean_command(text):
    text = text.strip()
    m = re.search(r"```(?:bash|sh|zsh|shell)?\s*\n?(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    return text.splitlines()[0].strip() if text else ""
