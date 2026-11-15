from pipeline.config import (
    ADAPTER_DIR,
    BASE_MODEL,
    CONFIG_PATH,
    DATA_DIR,
    GGUF_DIR,
    MERGED_DIR,
    SHELL_SYSTEM,
    SYSTEM_PROMPT,
    TRAIN_MODEL,
    VAL_HISTORY,
)
from pipeline.safety import BLOCKED, READ_ONLY, RISKY, clean_command, is_blocked, is_readonly, is_risky
from pipeline.data import (
    SHELL_SLOTS,
    SHELL_TEMPLATES,
    SOURCES,
    a_belebele,
    a_dolly,
    a_gsm8k,
    a_instruct,
    a_sciq,
    a_shell,
    a_squad,
    a_translate,
    cmd_prepare,
    gen_shell_synthetic,
)
from pipeline.training import (
    ANSI_RE,
    TRAIN_LOG,
    VAL_RES,
    _select_checkpoint,
    cmd_docker,
    cmd_merge,
    cmd_quantize,
    cmd_train,
)
from pipeline.inference import Generator, build_messages, cmd_test
from pipeline.ui import ART, BOT_NAME, PlainUI, RichUI
from pipeline.shell import _log_entry, cmd_shell, run_command, shell_flow
from pipeline.chat import CHAT_HELP, _chat_turn, _trim_history, cmd_chat
from pipeline.cli import main
from pipeline.config import CLI_DESCRIPTION as __doc__


if __name__ == "__main__":
    main()
