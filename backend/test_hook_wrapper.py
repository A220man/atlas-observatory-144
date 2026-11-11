import pytest
import json
import sys
sys.path.insert(0, '/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend')

from hook_wrapper import (
    fallback_response,
    handle_session_start,
    handle_user_prompt_submit,
    handle_pre_tool_use,
    handle_post_tool_use,
    handle_stop,
    handle_notification,
)

class TestHookWrapper:
    """Test hook wrapper behavior."""

    def test_fallback_response_always_continues(self):
        """fallback_response always returns continue=true."""
        result = json.loads(fallback_response("test_reason"))
        assert result["continue"] is True
        assert result["suppressOutput"] is True
        assert result["reason"] == "test_reason"

    @pytest.mark.asyncio
    async def test_pre_tool_use_always_continue(self):
        """PreToolUse always returns continue=true."""
        result = json.loads(await handle_pre_tool_use({"tool": "Read", "input": {}}))
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_post_tool_use_always_continue(self):
        """PostToolUse always returns continue=true."""
        result = json.loads(await handle_post_tool_use({"tool": "Write", "input": {}}))
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_stop_always_continue(self):
        """Stop always returns continue=true."""
        result = json.loads(await handle_stop({"session_id": "test"}))
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_notification_always_continue(self):
        """Notification always returns continue=true."""
        result = json.loads(await handle_notification({}))
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_user_prompt_submit_always_continue(self):
        """UserPromptSubmit always returns continue=true."""
        result = json.loads(await handle_user_prompt_submit({"prompt": "test"}))
        assert result["continue"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
