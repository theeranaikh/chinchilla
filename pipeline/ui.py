import contextlib
import time


BOT_NAME = "Gentleman"

ART = """[bold white]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣾⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⢂⠀⠀⠀⠀⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⠀
⠀⠀⠀⠀⠀⠀⢀⡈⠛⠦⠀⠀⠀⠆⠀⠀⠀⠀⡀⠀⠐⠀⠀⠀⠀⠀⠀⡛⢱⣿⣿⠀
⠀⠀⠀⠠⣤⣴⠝⢛⠂⠀⠀⣐⣤⣠⣤⣰⣤⣜⢀⠀⢀⠀⠀⠀⠀⠀⠀⡅⣸⣿⣿⠀
⠀⠀⠀⠀⢖⣂⠄⡀⣤⣶⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⡀⠀⠁⠀⠀⠀⠀⣇⣿⣿⣿⠀
⠀⠀⠀⠀⣤⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢿⣿⣿⣶⣦⠀⠀⠀⠀⢹⠹⣿⣿⠀
⠀⠀⠀⣤⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢟⣽⡪⠽⠛⡛⠻⣿⣷⠠⠀⠀⠀⠀⢻⣿⠀
⠀⠀⠀⢦⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⣠⣶⣾⣷⣤⡘⢟⡣⠀⠀⠀⠀⠘⣿⠀
⠀⠀⠀⡞⠿⢿⣿⣿⣿⣿⡿⣿⡿⠋⠀⣠⠾⣻⣽⠾⠻⣿⣿⡜⡷⡀⠀⠀⠀⢶⣿⠀
⠀⠀⠀⢠⣶⣤⣄⣀⠉⠻⢿⣶⡏⣡⡾⠗⣩⡀⣀⣶⣶⣾⣿⣿⡸⣧⠀⣢⠄⠸⣿⠀
⠀⠀⠀⠘⣿⠿⠛⠋⠋⠝⡃⣿⣿⣬⡻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⢰⡹⣼⠀⢿⠀
⠀⠀⠀⠀⣯⡰⣗⣴⣾⣿⢡⢹⣿⣎⢷⣽⣿⣿⣿⣿⣿⣿⣿⣿⣿⡁⢸⣛⡟⠀⣾⠀
⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⡏⢸⣿⣿⣎⠿⣿⣿⣿⣿⣿⣿⣿⡿⢹⣿⠀⠉⠀⣴⣿⠀
⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⡟⣿⣿⣿⣿⣿⡌⣿⣿⣿⣿⣿⡟⢠⣿⣿⠀⠀⠀⠉⢸⠀
⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⣏⠌⠋⣩⡶⣒⣵⣿⣿⣿⣿⣿⣷⣿⣿⣿⠀⠀⠀⠀⢸⠀
⠀⠀⠀⠀⠀⠀⠈⠙⢛⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⣻⣿⣿⣿⣿⡟⡄⢀⠀⠀⠈⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠐⢝⢿⣿⡛⢯⡶⢶⣒⣛⣧⣾⢿⣿⣿⣿⡿⢡⣿⠈⢧⡀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⡐⣶⣾⣿⣿⣿⠿⣻⣻⣿⣿⣿⡿⢡⣿⣿⡇⠆⢧⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢨⣭⣭⣥⣶⣾⣿⣿⣿⣿⡟⣡⣿⣿⣿⣿⢰⢸⡖⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⢊⡾⡁⠻⣿⣿⣿⣿⣿⣿⣿⠏⣰⣿⣿⣿⣿⣿⣼⡟⣿⠀
⠀⠀⠀⠀⠀⠀⠀⡠⣠⢳⣧⡺⠁⡄⣝⡻⠿⠿⠿⢛⣡⣾⣿⣿⣿⣿⣿⣿⢻⣧⣿⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/bold white]"""


class PlainUI:

    def banner(self, info):
        print("=" * 60)
        print(f" {BOT_NAME} chat  |  {info}")
        print(" พิมพ์ /help ดูคำสั่ง   !<คำขอ> = สั่งเทอร์มินัล   Ctrl-D = ออก")
        print("=" * 60)

    def loading(self):
        print("กำลังโหลดโมเดล...")
        return contextlib.nullcontext()

    def thinking(self):
        return contextlib.nullcontext()

    def prompt(self, mode):
        return input(f"\n[{mode}] › ")

    def info(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)

    def help(self, text):
        print(text)

    def command(self, cmd):
        print(f"$ {cmd}")

    def confirm(self, warn):
        return input(f"{warn}รันไหม? [y/N] ").strip().lower() == "y"

    def output(self, text, code):
        if text:
            print(text[-4000:])
        if code is not None:
            print(f"[exit {code}]")

    def reply(self, pieces):
        out = ""
        try:
            for p in pieces:
                print(p, end="", flush=True)
                out += p
        except KeyboardInterrupt:
            print("  [หยุดการตอบ]", end="")
        print()
        return out

    def bye(self):
        print("Good day to you, sir!")


class RichUI:

    def __init__(self, art=True):
        from rich.console import Console
        from rich.live import Live
        from rich.markdown import Markdown
        from rich.markup import escape
        from rich.panel import Panel
        from rich.prompt import Confirm, Prompt
        from rich.syntax import Syntax
        from rich.text import Text

        self.c = Console()
        self.art = art
        self.Live, self.Markdown, self.escape, self.Panel = Live, Markdown, escape, Panel
        self.Confirm, self.Prompt, self.Syntax, self.Text = Confirm, Prompt, Syntax, Text

    def banner(self, info):
        self.c.clear()
        body = (f"{ART}\n" if self.art else "") + (
            "[bold cyan]=== Welcome to Gentlemen Chat ===[/bold cyan]\n"
            "พิมพ์ [bold red]'exit'[/bold red] หรือ [bold red]'quit'[/bold red] เพื่อออกจากการสนทนา\n"
            f"[dim]{self.escape(info)}[/dim]"
        )
        panel = self.Panel(body, title="[bold yellow]🎩 Gentlemen Code CLI 🎩[/bold yellow]",
                           border_style="blue", expand=False, padding=(1, 2))
        self.c.print(panel, justify="center")
        self.c.print("[dim]/help = คำสั่งทั้งหมด · !<คำขอ> = สั่งเทอร์มินัล · Ctrl-D = ออก[/dim]", justify="center")
        self.c.print()

    def loading(self):
        return self.c.status("[bold cyan]กำลังโหลดโมเดล...[/bold cyan]", spinner="dots")

    def thinking(self):
        return self.c.status(f"[bold cyan]{BOT_NAME} กำลังคิด...[/bold cyan]", spinner="dots")

    def prompt(self, mode):
        return self.Prompt.ask(f"[bold green]❯ You[/bold green] [dim]({mode})[/dim]")

    def info(self, msg):
        self.c.print(f"[cyan]{self.escape(msg)}[/cyan]")

    def error(self, msg):
        self.c.print(f"[bold red]{self.escape(msg)}[/bold red]")

    def help(self, text):
        self.c.print(self.Panel(self.Text(text), title="[bold cyan]Help[/bold cyan]",
                                title_align="left", border_style="cyan", padding=(1, 2)))

    def command(self, cmd):
        self.c.print(self.Panel(self.Syntax(cmd, "bash", theme="ansi_dark", word_wrap=True),
                                title="[bold yellow]คำสั่ง[/bold yellow]", title_align="left",
                                border_style="yellow"))

    def confirm(self, warn):
        label = f"[yellow]{self.escape(warn)}[/yellow]" if warn else ""
        return self.Confirm.ask(f"{label}รันคำสั่งนี้ไหม?", default=False)

    def output(self, text, code):
        ok = code == 0
        title = "output" if code is None else f"output · exit {code}"
        body = self.Text(text[-4000:] if text else "(ไม่มี output)", style="" if text else "dim")
        self.c.print(self.Panel(body, title=title, title_align="left",
                                border_style="green" if ok else "red"))

    def _panel(self, text, sub=None):
        return self.Panel(self.Markdown(text), title=f"[bold blue]{BOT_NAME}[/bold blue]",
                          title_align="left", subtitle=sub, subtitle_align="right",
                          border_style="blue", padding=(1, 2))

    def reply(self, pieces):
        t0, text, stopped = time.time(), "", False
        it = iter(pieces)
        try:
            with self.thinking():
                first = next(it, None)
            if first is None:
                return ""
            text = first
            with self.Live(self._panel(text), console=self.c, refresh_per_second=12,
                           vertical_overflow="visible") as live:
                try:
                    for p in it:
                        text += p
                        live.update(self._panel(text))
                except KeyboardInterrupt:
                    stopped = True
                shown = text + ("\n\n*(หยุดการตอบ)*" if stopped else "")
                live.update(self._panel(shown, f"{time.time() - t0:.1f}s"))
        except KeyboardInterrupt:
            self.c.print("[dim](ยกเลิก)[/dim]")
        self.c.print()
        return text

    def bye(self):
        self.c.print(f"\n[bold blue]{BOT_NAME}:[/bold blue] Good day to you, sir! 🎩")
