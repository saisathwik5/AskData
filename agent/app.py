"""
app.py
FastAPI Server exposing streaming Server-Sent Events (SSE) for the AskData Agent.
Enables real-time step inspection for the Next.js UI and eval runner.
"""

import json
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import AskDataAgent
from tools import run_query

app = FastAPI(
    title="AskData Agent API",
    description="Streaming AI Analytics Agent with Java Guard Integration",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazily initialized agent
_agent_instance: Optional[AskDataAgent] = None

def get_agent() -> AskDataAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AskDataAgent()
    return _agent_instance

class ChatRequest(BaseModel):
    question: str
    userId: Optional[str] = "analyst-01"
    model: Optional[str] = None

@app.get("/health")
def health_check():
    """Checks the agent service health and verifies connectivity with the Java Guard."""
    guard_status = "unreachable"
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:8081/health", timeout=2) as resp:
            if resp.status == 200:
                guard_status = "connected (port 8081)"
    except Exception:
        pass

    return {
        "status": "healthy",
        "service": "AskData Python Agent",
        "java_guard": guard_status
    }

@app.post("/chat")
async def chat_streaming(request: ChatRequest):
    """
    Streams agent steps via Server-Sent Events (SSE).
    Each step (thought, tool_call, tool_result, guard_rejection, final_answer)
    is streamed as a JSON SSE event in real-time.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    agent = get_agent()

    async def event_generator():
        try:
            # Run generator
            for step in agent.run_step_by_step(
                question=request.question,
                user_id=request.userId or "analyst-01"
            ):
                payload = json.dumps(step, default=str)
                yield f"data: {payload}\n\n"
                await asyncio.sleep(0.01) # Yield to event loop
            yield "data: [DONE]\n\n"
        except Exception as e:
            err_payload = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {err_payload}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/chat/sync")
def chat_synchronous(request: ChatRequest):
    """Synchronous endpoint returning the final answer and complete step trace in one JSON payload."""
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    agent = get_agent()
    result = agent.ask(question=request.question, user_id=request.userId or "analyst-01")
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
