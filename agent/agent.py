"""
agent.py
Hand-crafted Python Text-to-SQL Agent Loop for AskData.
Coordinates model calls, tool execution, self-correction, token tracking, and streaming logs.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Generator, Optional
from openai import OpenAI

from prompts import SYSTEM_PROMPT
from tools import TOOLS_SCHEMA, execute_tool

# Pricing per million tokens (USD)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

def find_api_client():
    """Initializes the OpenAI client using either OPENAI_API_KEY or GEMINI_API_KEY."""
    # Check current environment, then .env files
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not openai_key or not gemini_key:
        possible_envs = [
            Path(__file__).parent / ".env",
            Path(__file__).parent.parent / ".env"
        ]
        for p in possible_envs:
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("OPENAI_API_KEY=") and not openai_key:
                            v = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if v and "sk-proj" in v:
                                openai_key = v
                        if line.startswith("GEMINI_API_KEY=") and not gemini_key:
                            v = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if v and "AIza" in v:
                                gemini_key = v

    if openai_key:
        return OpenAI(api_key=openai_key), "gpt-4o-mini"
    elif gemini_key:
        return OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ), "gemini-1.5-flash"
    else:
        raise ValueError("No API key found! Please set OPENAI_API_KEY or GEMINI_API_KEY in your .env file.")

def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["gpt-4o-mini"])
    cost = (prompt_tokens / 1_000_000.0) * pricing["input"] + (completion_tokens / 1_000_000.0) * pricing["output"]
    return round(cost, 6)

class AskDataAgent:
    def __init__(self, model_name: Optional[str] = None):
        self.client, default_model = find_api_client()
        self.model_name = model_name or default_model
        print(f"[AskDataAgent] Initialized using model: {self.model_name}")

    def run_step_by_step(self, question: str, user_id: str = "analyst-01", max_steps: int = 8) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        The Hand-Crafted Agent Loop:
        1. Sends user question with system prompt & tool definitions.
        2. Inspects model response:
           - If tool calls requested -> executes tool, feeds result back.
           - If text returned -> emits final answer / clarification.
        3. Enforces step limit (max_steps) and logs tokens/cost.
        Yields each step for live streaming (SSE/CLI).
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]

        total_prompt_tokens = 0
        total_completion_tokens = 0
        step_number = 1
        retries_count = 0
        charts_generated = []

        yield {
            "type": "start",
            "step": 0,
            "question": question,
            "user_id": user_id,
            "model": self.model_name
        }

        while step_number <= max_steps:
            # Call the LLM
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.1
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "step": step_number,
                    "message": f"Model invocation failed: {str(e)}"
                }
                return

            choice = response.choices[0]
            msg = choice.message
            usage = response.usage

            if usage:
                p_tok = usage.prompt_tokens
                c_tok = usage.completion_tokens
                total_prompt_tokens += p_tok
                total_completion_tokens += c_tok
                step_cost = calculate_cost(self.model_name, p_tok, c_tok)
            else:
                p_tok, c_tok, step_cost = 0, 0, 0.0

            # Check if model wants to call tools
            if msg.tool_calls:
                # Append assistant message with tool calls to conversation
                messages.append(msg)

                for tool_call in msg.tool_calls:
                    fn_name = tool_call.function.name
                    raw_args = tool_call.function.arguments

                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}

                    yield {
                        "type": "tool_call",
                        "step": step_number,
                        "tool": fn_name,
                        "arguments": args,
                        "thought": msg.content or ""
                    }

                    # Execute the tool
                    result = execute_tool(fn_name, args, user_id=user_id, question=question)

                    # If chart was created, store it
                    if fn_name == "make_chart":
                        charts_generated.append(result)

                    # Check for guard error to track retries
                    if fn_name == "run_query" and isinstance(result, dict) and not result.get("success", True):
                        retries_count += 1
                        yield {
                            "type": "guard_rejection",
                            "step": step_number,
                            "rejection": result.get("error", "Query blocked by guard"),
                            "retries_so_far": retries_count
                        }

                    yield {
                        "type": "tool_result",
                        "step": step_number,
                        "tool": fn_name,
                        "result": result
                    }

                    # Append tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str)
                    })

                step_number += 1

            else:
                # Model did not call a tool -> It has provided its final response (answer, clarification, or refusal)
                final_answer = msg.content or ""
                messages.append({"role": "assistant", "content": final_answer})

                total_cost = calculate_cost(self.model_name, total_prompt_tokens, total_completion_tokens)

                yield {
                    "type": "final_answer",
                    "step": step_number,
                    "answer": final_answer,
                    "charts": charts_generated,
                    "metrics": {
                        "total_steps": step_number,
                        "prompt_tokens": total_prompt_tokens,
                        "completion_tokens": total_completion_tokens,
                        "total_tokens": total_prompt_tokens + total_completion_tokens,
                        "estimated_cost_usd": total_cost,
                        "guard_retries": retries_count
                    }
                }
                return

        # Max steps exceeded
        yield {
            "type": "max_steps_exceeded",
            "step": step_number,
            "message": f"Agent exceeded maximum allowed steps ({max_steps}) without reaching a final answer."
        }

    def ask(self, question: str, user_id: str = "analyst-01") -> Dict[str, Any]:
        """Convenience method that runs the generator and returns the final answer."""
        final_result = None
        all_steps = []
        for step in self.run_step_by_step(question, user_id=user_id):
            all_steps.append(step)
            if step["type"] == "final_answer":
                final_result = step

        if final_result:
            final_result["steps_trace"] = all_steps
            return final_result
        return {
            "type": "error",
            "answer": "Failed to generate answer within step limit.",
            "steps_trace": all_steps
        }
