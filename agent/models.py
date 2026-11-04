"""
models.py
Universal Multi-Model Adapter Interface for Category 7.
Provides a unified abstraction: generate(messages, tools) -> NormalizedResponse.
Priority Order:
  1st: Google Gemini (gemini-1.5-flash / gemini-2.0-flash)
  2nd: OpenAI / ChatGPT (gpt-4o-mini / gpt-4o)
  3rd: Anthropic Claude (claude-3-5-sonnet)
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class NormalizedToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class NormalizedResponse:
    content: Optional[str] = None
    tool_calls: List[NormalizedToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""

class ModelAdapter:
    """Base interface for model provider adapters."""
    def generate(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> NormalizedResponse:
        raise NotImplementedError

class OpenAIAdapter(ModelAdapter):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", base_url: Optional[str] = None):
        from openai import OpenAI
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> NormalizedResponse:
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools if tools else None,
            temperature=0.1
        )
        choice = resp.choices[0]
        msg = choice.message

        normalized_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                normalized_calls.append(NormalizedToolCall(
                    id=tc.id or f"call_{tc.function.name}",
                    name=tc.function.name,
                    arguments=args
                ))

        usage = TokenUsage()
        if resp.usage:
            usage.prompt_tokens = resp.usage.prompt_tokens
            usage.completion_tokens = resp.usage.completion_tokens
            usage.total_tokens = resp.usage.total_tokens

        return NormalizedResponse(
            content=msg.content,
            tool_calls=normalized_calls,
            usage=usage,
            model=self.model_name
        )

class ClaudeAdapter(ModelAdapter):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        import anthropic
        self.model_name = model_name
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> NormalizedResponse:
        system_content = ""
        claude_messages = []
        for m in messages:
            if m["role"] == "system":
                system_content += m["content"] + "\n"
            elif m["role"] == "tool":
                claude_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id"),
                        "content": str(m.get("content", ""))
                    }]
                })
            elif m["role"] == "assistant":
                if "tool_calls" in m and m["tool_calls"]:
                    blocks = []
                    if m.get("content"):
                        blocks.append({"type": "text", "text": m["content"]})
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id"),
                            "name": fn.get("name"),
                            "input": json.loads(args) if isinstance(args, str) else args
                        })
                    claude_messages.append({"role": "assistant", "content": blocks})
                else:
                    claude_messages.append({"role": "assistant", "content": m.get("content", "")})
            else:
                claude_messages.append({"role": m["role"], "content": m.get("content", "")})

        claude_tools = []
        for t in tools:
            fn = t["function"]
            claude_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
            })

        response = self.client.messages.create(
            model=self.model_name,
            system=system_content.strip(),
            messages=claude_messages,
            tools=claude_tools if claude_tools else None,
            max_tokens=2048,
            temperature=0.1
        )

        content_text = ""
        normalized_calls = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                normalized_calls.append(NormalizedToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input if isinstance(block.input, dict) else {}
                ))

        usage = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens
        )

        return NormalizedResponse(
            content=content_text if content_text else None,
            tool_calls=normalized_calls,
            usage=usage,
            model=self.model_name
        )

def load_env_file():
    """Finds and loads .env keys into os.environ if not already present."""
    possible_envs = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    for p in possible_envs:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
            break

def get_model_adapter() -> ModelAdapter:
    """
    Factory creating the appropriate ModelAdapter based on user preference:
      1st Preference: Google Gemini (fast, affordable, powerful function calling)
      2nd Preference: OpenAI (ChatGPT)
      3rd Preference: Anthropic (Claude)
    """
    load_env_file()
    provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # 1st Preference: Google Gemini (default)
    if provider == "gemini":
        if not gemini_key:
            # Fall back to OpenAI if Gemini key missing
            if openai_key:
                print("[ModelAdapter] GEMINI_API_KEY not found, falling back to OpenAI (2nd Preference)")
                model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                return OpenAIAdapter(api_key=openai_key, model_name=model)
            raise ValueError("MODEL_PROVIDER=gemini requested, but GEMINI_API_KEY is not set.")
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        print(f"[ModelAdapter] Initializing Google Gemini ({model}) [1st Preference]")
        return OpenAIAdapter(
            api_key=gemini_key,
            model_name=model,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    # 2nd Preference: OpenAI / ChatGPT
    if provider in ["openai", "chatgpt"]:
        if not openai_key:
            raise ValueError(f"MODEL_PROVIDER={provider} requested, but OPENAI_API_KEY is not set.")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"[ModelAdapter] Initializing OpenAI ({model}) [2nd Preference]")
        return OpenAIAdapter(api_key=openai_key, model_name=model)

    # 3rd Preference: Anthropic Claude
    if provider in ["anthropic", "claude"]:
        if not anthropic_key:
            raise ValueError(f"MODEL_PROVIDER={provider} requested, but ANTHROPIC_API_KEY is not set.")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        print(f"[ModelAdapter] Initializing Anthropic Claude ({model}) [3rd Preference]")
        return ClaudeAdapter(api_key=anthropic_key, model_name=model)

    # 2nd Preference: OpenAI / ChatGPT (Fallback)
    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"[ModelAdapter] Falling back to OpenAI ({model}) [2nd Preference / Fallback]")
        return OpenAIAdapter(api_key=openai_key, model_name=model)

    # 3rd Preference: Anthropic Claude
    if anthropic_key:
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        print(f"[ModelAdapter] Falling back to Claude ({model}) [3rd Preference]")
        return ClaudeAdapter(api_key=anthropic_key, model_name=model)

    raise ValueError("No valid API key found. Please set GEMINI_API_KEY or OPENAI_API_KEY in your .env file.")
