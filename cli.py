"""
cli.py
Root entrypoint for AskData CLI.
Allows running directly from AskData root directory:
  uv run python cli.py "What is our current Monthly Recurring Revenue (MRR) in USD?"
"""

import sys
from pathlib import Path

# Add agent directory to sys.path
agent_dir = Path(__file__).parent / "agent"
sys.path.insert(0, str(agent_dir))

from cli import run_cli

if __name__ == "__main__":
    run_cli()
