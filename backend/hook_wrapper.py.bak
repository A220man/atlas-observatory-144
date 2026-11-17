#!/usr/bin/env python3
"""
Thin, fail-open hook wrapper for Claude Code.
No login shell spawn in common path.
Worker unavailable returns {continue:true} exit 0.
"""
import sys
import json
import os
import time
import asyncio
from pathlib import Path

API_BASE = os.environ.get("CLAUDE_MEM_API_BASE", "http://127.0.0.1:8000")
TIMEOUT_MS = int(os.environ.get("CLAUDE_MEM_HOOK_TIMEOUT_MS", "5000"))

def fallback_response(reason: str) -> str:
    """Always return continue=true with exit 0."""
    return json.dumps({"continue": True, "suppressOutput": True, "reason": reason})

async def check_worker_health() -> bool:
    """Quick health check with timeout."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
            resp = await client.get(f"{API_BASE}/health")
            return resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:
        return False

async def handle_session_start(payload: dict) -> str:
    """SessionStart: return context if worker healthy, else fail open."""
    if not await check_worker_health():
        return fallback_response("worker_unavailable")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
            resp = await client.post(f"{API_BASE}/context", json={
                "project_id": payload.get("project_id"),
                "query": payload.get("cwd", ""),
                "limit": 10
            })
            if resp.status_code == 200:
                observations = resp.json()
                if observations:
                    ctx = "\n".join([f"- {o['title']}: {o['narrative'][:200]}" for o in observations[:5]])
                    return json.dumps({"continue": True, "additionalContext": f"Relevant context:\n{ctx}"})
    except Exception:
        pass
    return fallback_response("session_start_ok")

async def handle_user_prompt_submit(payload: dict) -> str:
    """UserPromptSubmit: enqueue prompt, fail open if worker down."""
    if not await check_worker_health():
        return fallback_response("worker_unavailable")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
            await client.post(f"{API_BASE}/user-prompts", json=payload)
    except Exception:
        pass
    return fallback_response("user_prompt_submit_ok")

async def handle_pre_tool_use(payload: dict) -> str:
    """PreToolUse: fail open always."""
    return fallback_response("pre_tool_use_ok")

async def handle_post_tool_use(payload: dict) -> str:
    """PostToolUse: fire-and-forget capture, fail open."""
    if await check_worker_health():
        try:
            import httpx
            async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
                await client.post(f"{API_BASE}/observations", json=payload)
        except Exception:
            pass
    return fallback_response("post_tool_use_ok")

async def handle_stop(payload: dict) -> str:
    """Stop: trigger summarization if session complete, fail open."""
    if await check_worker_health():
        try:
            import httpx
            async with httpx.AsyncClient(timeout=TIMEOUT_MS / 1000) as client:
                session_id = payload.get("session_id")
                if session_id:
                    await client.post(f"{API_BASE}/sessions/{session_id}/complete")
        except Exception:
            pass
    return fallback_response("stop_ok")

async def handle_notification(payload: dict) -> str:
    """Notification: no-op, fail open."""
    return fallback_response("notification_ok")

async def main():
    if len(sys.argv) < 2:
        print(fallback_response("missing_hook_type"))
        return
    
    hook_type = sys.argv[1]
    start_time = time.perf_counter()
    
    # Read stdin once, defensively
    try:
        stdin_data = sys.stdin.read()
        payload = json.loads(stdin_data) if stdin_data.strip() else {}
    except Exception:
        payload = {}
    
    handlers = {
        "session_start": handle_session_start,
        "user_prompt_submit": handle_user_prompt_submit,
        "pre_tool_use": handle_pre_tool_use,
        "post_tool_use": handle_post_tool_use,
        "stop": handle_stop,
        "notification": handle_notification,
    }
    
    handler = handlers.get(hook_type)
    if handler:
        try:
            result = await handler(payload)
            print(result)
        except Exception as e:
            print(fallback_response(f"handler_error: {str(e)[:50]}"))
    else:
        print(fallback_response("unknown_hook_type"))
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    if elapsed_ms > 100:
        print(f"[hook_wrapper] {hook_type} took {elapsed_ms:.1f}ms", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
