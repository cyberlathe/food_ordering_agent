"""
display.py
----------
All terminal output lives here. Uses the `rich` library for colored,
structured output so students can visually distinguish each agent component.

Color coding:
  🟣 Purple  → Memory updates
  🔵 Blue    → Think phase
  🟡 Yellow  → Plan phase
  🟠 Orange  → Act phase (tool calls)
  🟢 Green   → Observe phase
  ✨ Cyan    → Answer phase
  ⚪ White   → User / system messages
"""

import json
from typing import Any

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.columns import Columns

console = Console()

# ── Phase colors ──────────────────────────────────────────────────────────────
PHASE_STYLES = {
    "think":   ("THINK",   "bold blue",          "blue"),
    "plan":    ("PLAN",    "bold magenta",        "magenta"),
    "act":     ("ACT",     "bold yellow",         "yellow"),
    "observe": ("OBSERVE", "bold green",          "green"),
    "answer":  ("ANSWER",  "bold cyan",           "cyan"),
}


def print_welcome():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🤖  AI Agent — Educational Demo[/bold cyan]\n"
        "[dim]MCP · Memory · Reasoning Loop · Tools[/dim]\n\n"
        "[dim]Commands:  [bold]quit[/bold] · [bold]memory[/bold] · [bold]clear[/bold] · [bold]help[/bold][/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def print_help():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold cyan]quit[/bold cyan]",   "Exit the agent")
    table.add_row("[bold cyan]memory[/bold cyan]",  "Show everything stored in memory")
    table.add_row("[bold cyan]clear[/bold cyan]",   "Clear conversation history (keeps memory)")
    table.add_row("[bold cyan]reset[/bold cyan]",   "Clear both history AND memory")
    console.print(Panel(table, title="[bold]Commands[/bold]", border_style="dim"))


def print_user_prompt():
    console.print()
    return console.input("[bold white]You ▶[/bold white] ")


def print_turn_separator(turn: int):
    console.print()
    console.print(Rule(f"[dim]Turn {turn}[/dim]", style="dim"))


def print_mode_banner(use_mock: bool):
    mode = "[yellow]MOCK MODE[/yellow] — using fake data"
    console.print(f"\n  {mode}\n")


# ── Memory ────────────────────────────────────────────────────────────────────

def print_memory_panel(facts: dict[str, Any]):
    if not facts:
        console.print(Panel("[dim]Nothing stored yet.[/dim]",
                            title="[bold purple]🧠  Memory[/bold purple]",
                            border_style="purple"))
        return

    table = Table(show_header=True, header_style="bold purple", box=None, padding=(0, 2))
    table.add_column("Key", style="purple")
    table.add_column("Value")
    for k, v in facts.items():
        table.add_row(str(k), str(v))

    console.print(Panel(table,
                        title="[bold purple]🧠  Memory[/bold purple]",
                        border_style="purple"))


def print_memory_update(key: str, value: Any):
    console.print(f"  [bold purple]🧠  Memory[/bold purple]  [purple]{key}[/purple] ← [white]{value}[/white]")

# ── History ──────────────────────────────────────────────────────────

def print_history_panel(history: list[dict]):
    if not history:
        console.print(Panel("[dim]No conversation history yet.[/dim]",
                            title="[bold dim]Conversation History[/bold dim]",
                            border_style="dim"))
        return

    panels = []
    for turn in history:
        role = turn.get("role", "unknown").upper()
        content = turn.get("content", "")
        panels.append(Panel(content, title=f"[bold]{role}[/bold]", border_style="dim"))

    console.print(Panel(Columns(panels),
                        title="[bold dim]Conversation History[/bold dim]",
                        border_style="dim",
                        padding=(1, 2)))

# ── Reasoning phases ──────────────────────────────────────────────────────────

def print_phase(phase: str, text: str):
    label, label_style, border_style = PHASE_STYLES.get(
        phase, (phase.upper(), "bold white", "white"))
    console.print(Panel(
        f"[{label_style}][{label}][/{label_style}]  {text}",
        border_style=border_style,
        padding=(0, 2),
    ))


def print_reasoning_block(steps: list[dict]):
    console.print()
    console.print(Rule("[bold]Reasoning Loop[/bold]", style="dim"))
    for step in steps:
        print_phase(step.get("phase", ""), step.get("text", ""))


# ── Tool calls ────────────────────────────────────────────────────────────────

def print_tool_call(tool: str, input_data: dict, result_summary: str, mock: bool):
    tag = "[yellow][MOCK][/yellow]" if mock else "[green][LIVE][/green]"
    input_str = json.dumps(input_data, indent=2) if input_data else "{}"
    body = (
        f"{tag} [bold yellow]{tool}[/bold yellow]\n\n"
        f"[dim]Input:[/dim]\n[yellow]{input_str}[/yellow]\n\n"
        f"[dim]Result summary:[/dim]\n{result_summary}"
    )
    console.print(Panel(body,
                        title="[bold yellow]🔧  Tool Call[/bold yellow]",
                        border_style="yellow",
                        padding=(0, 2)))


# ── Agent reply ───────────────────────────────────────────────────────────────

def print_agent_reply(text: str):
    console.print()
    console.print(Panel(
        text,
        title="[bold cyan]🤖  Agent[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()


# ── Errors / status ───────────────────────────────────────────────────────────

def print_error(msg: str):
    console.print(f"\n[bold red]✗  Error:[/bold red] {msg}\n")


def print_status(msg: str):
    console.print(f"\n[dim]{msg}[/dim]")


def print_raw_json(data: Any):
    console.print(Panel(
        json.dumps(data, indent=2),
        title="[dim]Raw JSON[/dim]",
        border_style="dim",
    ))
