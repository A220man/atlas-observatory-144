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
        "session_start": lambda p: fallback_response("session_start_ok"),
        "user_prompt_submit": lambda p: fallback_response("user_prompt_submit_ok"),
        "pre_tool_use": lambda p: fallback_response("pre_tool_use_ok"),
        "post_tool_use": lambda p: fallback_response("post_tool_use_ok"),
        "stop": lambda p: fallback_response("stop_ok"),
        "notification": lambda p: fallback_response("notification_ok"),
    }
    
    handler = handlers.get(hook_type)
    if handler:
        try:
            result = handler(payload)  # sync call, no await
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
