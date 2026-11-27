import pytest
import json
import subprocess
import sys
sys.path.insert(0, '/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend')

from hook_wrapper import fallback_response

class TestHookWrapper:
    """Test hook wrapper behavior."""

    def test_fallback_response_always_continues(self):
        """fallback_response always returns continue=true."""
        result = json.loads(fallback_response("test_reason"))
        assert result["continue"] is True
        assert result["suppressOutput"] is True
        assert result["reason"] == "test_reason"

    @pytest.mark.asyncio
    async def test_cli_session_start(self):
        """CLI invocation with session_start returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "session_start"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "session_start_ok"

    @pytest.mark.asyncio
    async def test_cli_pre_tool_use(self):
        """CLI invocation with pre_tool_use returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "pre_tool_use"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "pre_tool_use_ok"

    @pytest.mark.asyncio
    async def test_cli_post_tool_use(self):
        """CLI invocation with post_tool_use returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "post_tool_use"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "post_tool_use_ok"

    @pytest.mark.asyncio
    async def test_cli_stop(self):
        """CLI invocation with stop returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "stop"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "stop_ok"

    @pytest.mark.asyncio
    async def test_cli_notification(self):
        """CLI invocation with notification returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "notification"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "notification_ok"

    @pytest.mark.asyncio
    async def test_cli_unknown(self):
        """CLI invocation with unknown hook type returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "unknown_type"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "unknown_hook_type"

    @pytest.mark.asyncio
    async def test_cli_no_args(self):
        """CLI invocation with no hook type returns continue=true."""
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py"],
            capture_output=True, text=True, timeout=5
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True

    @pytest.mark.asyncio
    async def test_cli_disabled_env_short_circuits(self):
        """CLAUDE_MEM_DISABLE short-circuits to continue=true without reading stdin."""
        import os
        env = dict(os.environ)
        env["CLAUDE_MEM_DISABLE"] = "1"
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "session_start"],
            capture_output=True, text=True, timeout=5, env=env,
            input="this-is-not-json-stdin"
        )
        assert proc.returncode == 0, f"Expected exit 0, got {proc.returncode}: {proc.stdout} {proc.stderr}"
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "hooks_disabled"

    @pytest.mark.asyncio
    async def test_disable_tool_hooks_alias(self):
        """CLAUDE_MEM_DISABLE_TOOL_HOOKS also short-circuits."""
        import os
        env = dict(os.environ)
        env["CLAUDE_MEM_DISABLE_TOOL_HOOKS"] = "1"
        proc = subprocess.run(
            [sys.executable, "/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend/hook_wrapper.py", "post_tool_use"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        assert proc.returncode == 0
        result = json.loads(proc.stdout.strip())
        assert result["continue"] is True
        assert result["reason"] == "hooks_disabled"
