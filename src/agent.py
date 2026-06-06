"""
agent.py
--------
Main entry point. Runs the interactive REPL (Read-Eval-Print Loop).

CONCEPT FOR BEGINNERS
--------------------
REPL = the loop that keeps the agent alive:
  1. READ    — get input from the user
  2. EVAL    — run the reasoning loop
  3. PRINT   — show the agent's response
  4. LOOP    — go back to step 1

Usage:
  python agent.py
  python agent.py --raw
  SHOW_RAW_JSON=true python agent.py  # also print raw LLM JSON output

"""

import sys
import os

# ── Allow running from project root ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

import config as config

# ── Parse CLI flags before imports that read config ───────────────────────────
if "--raw" in sys.argv:
    config.SHOW_RAW_JSON = True

import display as display
from memory import Memory
from llm import LLMClient
from reasoning import run_turn


def main():
    display.print_welcome()

    # Initialise components
    memory = Memory()

    try:
        llm = LLMClient()
    except ValueError as e:
        display.print_error(str(e))
        sys.exit(1)

    turn = 0

    display.print_agent_reply("What would you like to order today? 🍔🍕🍣\n")
    while True:
        try:
            user_input = display.print_user_prompt()
        except (EOFError, KeyboardInterrupt):
            display.print_status("Goodbye! 👋")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # ── Built-in commands ─────────────────────────────────────────────────
        cmd = user_input.lower()

        if cmd in ("quit", "exit", "bye", "q"):
            display.print_status("Goodbye! 👋")
            break

        if cmd == "help":
            display.print_help()
            continue

        if cmd == "memory":
            display.print_memory_panel(memory.all())
            continue

        if cmd == "clear":
            llm.clear_history()
            display.print_status("Conversation history cleared. Memory intact.")
            turn = 0
            continue

        if cmd == "history":
            display.print_history_panel(llm.history)
            continue

        if cmd == "reset":
            llm.clear_history()
            memory.clear()
            display.print_status("History and memory both cleared.")
            turn = 0
            continue

        # ── Normal turn ───────────────────────────────────────────────────────
        turn += 1
        display.print_turn_separator(turn)

        try:
            run_turn(
                user_message=user_input,
                llm_client=llm,
                memory=memory,
            )
        except Exception as e:
            display.print_error(f"Turn failed: {e}")
            if "--debug" in sys.argv:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
