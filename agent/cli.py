"""
cli.py
Command-line interface for the AskData Agent.
Allows asking questions directly from terminal, viewing real-time steps,
and verifying numerical accuracy against our golden eval dataset.
"""

import sys
import json
from agent import AskDataAgent

# Color formatting helpers for terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

SAMPLE_QUESTIONS = [
    "What is our current Monthly Recurring Revenue (MRR) in USD?",
    "What is our total net revenue to date in USD?",
    "How many paying customers do we have right now?",
    "Which 5 users have executed the highest number of queries?",
    "What is our gross revenue in EUR?",
    "How are we doing? (Test vague handling)",
    "What is our Net Promoter Score (NPS)? (Test impossible handling)",
    "SELECT email FROM users (Test security refusal)"
]

def print_step(step: dict):
    stype = step.get("type")
    snum = step.get("step", 0)

    if stype == "start":
        print(f"\n{BOLD}{CYAN}=== AskData Agent Starting ==={RESET}")
        print(f"Question: {BOLD}\"{step.get('question')}\"{RESET}")
        print(f"Model: {step.get('model')}\n")

    elif stype == "tool_call":
        tool = step.get("tool")
        args = step.get("arguments", {})
        print(f"{YELLOW}[Step {snum} -> Calling Tool: {tool}]{RESET}")
        if tool == "run_query":
            print(f"  SQL: {CYAN}{args.get('sql')}{RESET}")
        else:
            print(f"  Args: {args}")

    elif stype == "tool_result":
        tool = step.get("tool")
        res = step.get("result")
        if tool == "run_query" and isinstance(res, dict):
            if res.get("success"):
                print(f"  {GREEN}[Guard Approved & Executed in {res.get('executionTimeMs')}ms]{RESET}")
                print(f"  Rows ({res.get('rowCount')}): {res.get('rows')[:3]}")
            else:
                print(f"  {RED}[Guard Error: {res.get('error')}]{RESET}")
        else:
            print(f"  Result: {str(res)[:160]}...")
        print()

    elif stype == "guard_rejection":
        print(f"  {RED}[Self-Correction Triggered: {step.get('rejection')}]{RESET}\n")

    elif stype == "final_answer":
        print(f"{BOLD}{GREEN}=== Final Answer ==={RESET}")
        print(f"{step.get('answer')}\n")

        metrics = step.get("metrics", {})
        print(f"{BOLD}--- Run Statistics ---{RESET}")
        print(f"Steps:             {metrics.get('total_steps')}")
        print(f"Prompt Tokens:     {metrics.get('prompt_tokens'):,}")
        print(f"Completion Tokens: {metrics.get('completion_tokens'):,}")
        print(f"Total Tokens:      {metrics.get('total_tokens'):,}")
        print(f"Estimated Cost:    ${metrics.get('estimated_cost_usd'):.6f}")
        print(f"Guard Retries:     {metrics.get('guard_retries')}")
        print("======================\n")

    elif stype == "error":
        print(f"{RED}[Error]: {step.get('message')}{RESET}\n")

def run_cli():
    print(f"{BOLD}AskData Analytics CLI Agent{RESET}")
    print("Connecting to agent core...\n")

    try:
        agent = AskDataAgent()
    except Exception as e:
        print(f"{RED}Failed to initialize agent: {e}{RESET}")
        sys.exit(1)

    if len(sys.argv) > 1:
        # One-shot command line question
        question = " ".join(sys.argv[1:])
        for step in agent.run_step_by_step(question):
            print_step(step)
        return

    # Interactive mode
    print("Sample Questions to try:")
    for idx, q in enumerate(SAMPLE_QUESTIONS, 1):
        print(f"  [{idx}] {q}")
    print("\nType a question, a sample number (1-8), or 'exit' to quit.\n")

    while True:
        try:
            user_input = input(f"{BOLD}AskData > {RESET}").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            if user_input.isdigit() and 1 <= int(user_input) <= len(SAMPLE_QUESTIONS):
                question = SAMPLE_QUESTIONS[int(user_input) - 1]
            else:
                question = user_input

            for step in agent.run_step_by_step(question):
                print_step(step)

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    run_cli()
