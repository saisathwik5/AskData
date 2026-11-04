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

from prompts import SYSTEM_PROMPT
from context import build_system_prompt
from tools import TOOLS_SCHEMA, execute_tool
from models import get_model_adapter, ModelAdapter, NormalizedResponse

# Pricing per million tokens (USD)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.5-flash": {"input": 0.10, "output": 0.40},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
}

def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["gemini-1.5-flash"])
    cost = (prompt_tokens / 1_000_000.0) * pricing["input"] + (completion_tokens / 1_000_000.0) * pricing["output"]
    return round(cost, 6)

class AskDataAgent:
    def __init__(self, model_adapter: Optional[ModelAdapter] = None, context_level: str = "full", 
                 user_role: str = "analyst", reference_date: str = "2025-06-30"):
        self.adapter = model_adapter or get_model_adapter()
        self.model_name = getattr(self.adapter, "model_name", "llm-agent")
        self.context_level = context_level
        self.user_role = user_role
        self.reference_date = reference_date
        print(f"[AskDataAgent] Initialized using adapter: {self.model_name} | Context: {self.context_level}")

    def run_step_by_step(self, question: str, user_id: str = "analyst-01", max_steps: int = 8) -> Generator[Dict[str, Any], None, Dict[str, Any]]:
        """
        The Hand-Crafted Agent Loop:
        1. Sends user question with system prompt (built from context layers) & tool definitions.
        2. Inspects model response:
           - If tool calls requested -> executes tool, feeds result back.
           - If text returned -> emits final answer / clarification.
        3. Enforces step limit (max_steps) and logs tokens/cost.
        Yields each step for live streaming (SSE/CLI).
        """
        system_prompt = build_system_prompt(
            context_level=self.context_level,
            user_role=self.user_role,
            reference_date=self.reference_date
        )

        messages = [
            {"role": "system", "content": system_prompt},
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
            # Call the LLM through the unified adapter
            try:
                response = self.adapter.generate(
                    messages=messages,
                    tools=TOOLS_SCHEMA
                )
            except Exception as e:
                yield {
                    "type": "error",
                    "step": step_number,
                    "message": f"Model invocation failed: {str(e)}"
                }
                return

            usage = response.usage
            p_tok = usage.prompt_tokens
            c_tok = usage.completion_tokens
            total_prompt_tokens += p_tok
            total_completion_tokens += c_tok
            step_cost = calculate_cost(self.model_name, p_tok, c_tok)

            # Check if model wants to call tools
            if response.tool_calls:
                # Append assistant message with tool calls to conversation
                raw_tool_calls_dict = []
                for tc in response.tool_calls:
                    raw_tool_calls_dict.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    })

                messages.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": raw_tool_calls_dict
                })

                for tool_call in response.tool_calls:
                    fn_name = tool_call.name
                    args = tool_call.arguments

                    yield {
                        "type": "tool_call",
                        "step": step_number,
                        "tool": fn_name,
                        "arguments": args,
                        "thought": response.content or ""
                    }

                    # Execute the tool
                    result = execute_tool(fn_name, args, user_id=user_id, question=question)

                    if fn_name == "make_chart":
                        charts_generated.append(result)

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

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str)
                    })

                step_number += 1

            else:
                final_answer = response.content or ""
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
