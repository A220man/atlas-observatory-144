import pytest
from observer_pipeline import (
    OutputClass,
    BatchDecision,
    TokenBudget,
    classify_output,
    process_model_output,
    truncate_history,
    estimate_tokens,
    POLICY_TABLE,
    DEFAULT_BUDGET,
)


class TestOutputClass:
    """Test output classification."""
    
    def test_empty_output_is_idle(self):
        result = classify_output("")
        assert result.output_class == OutputClass.IDLE
        assert result.decision == BatchDecision.PRESERVE
    
    def test_whitespace_output_is_idle(self):
        result = classify_output("   \n\t  ")
        assert result.output_class == OutputClass.IDLE
    
    def test_skip_summary_is_skip(self):
        result = classify_output('<skip_summary reason="nothing to do"/>')
        assert result.output_class == OutputClass.SKIP
        assert result.decision == BatchDecision.CONFIRM
        assert result.salvageable_content == "nothing to do"
    
    def test_skip_observation_is_skip(self):
        result = classify_output('<skip_observation/>')
        assert result.output_class == OutputClass.SKIP
        assert result.decision == BatchDecision.CONFIRM
    
    def test_auth_failure_is_auth(self):
        for text in [
            "Failed to authenticate 403",
            "401 Unauthorized",
            "Not logged in",
            "OAuth session expired",
            "Authentication failed: invalid token",
        ]:
            result = classify_output(text)
            assert result.output_class == OutputClass.AUTH, f"Failed for: {text}"
            assert result.decision == BatchDecision.PRESERVE
    
    def test_context_overflow_is_overflow(self):
        for text in [
            "Prompt is too long",
            "Context overflow: maximum context length exceeded",
            "Token limit exceeded",
        ]:
            result = classify_output(text)
            assert result.output_class == OutputClass.OVERFLOW, f"Failed for: {text}"
            assert result.decision == BatchDecision.PRESERVE
    
    def test_model_error_is_prose_abort(self):
        for text in [
            "There's an issue with the selected model",
            "Model error: service unavailable",
            "Internal server error 500",
        ]:
            result = classify_output(text)
            assert result.output_class == OutputClass.PROSE, f"Failed for: {text}"
            assert result.decision == BatchDecision.ABORT
            assert result.abort_reason is not None
    
    def test_transport_error_preserves_batch(self):
        for text in [
            "Connection closed mid-response",
            "Connection reset by peer",
            "Network error: timeout",
        ]:
            result = classify_output(text)
            # Transport errors are classified as AUTH (preserve batch)
            assert result.output_class in (OutputClass.AUTH, OutputClass.PROSE)
            assert result.decision == BatchDecision.PRESERVE
    
    def test_valid_observation_xml_is_valid(self):
        text = """
        <observation>
            <type>bugfix</type>
            <title>Fix login bug</title>
            <narrative>Fixed the login authentication issue</narrative>
        </observation>
        """
        result = classify_output(text)
        assert result.output_class == OutputClass.VALID
        assert result.decision == BatchDecision.CONFIRM
        assert result.observations is not None
        assert len(result.observations) == 1
        assert result.observations[0]["type"] == "bugfix"
        assert result.observations[0]["title"] == "Fix login bug"
    
    def test_multiple_observations(self):
        text = """
        <observation><type>bugfix</type><title>Fix A</title><narrative>A</narrative></observation>
        <observation><type>feature</type><title>Add B</title><narrative>B</narrative></observation>
        """
        result = classify_output(text)
        assert result.output_class == OutputClass.VALID
        assert len(result.observations) == 2
    
    def test_xml_drift_kind_detail(self):
        text = """
        <observation>
            <kind>bugfix</kind>
            <detail>Fix login</detail>
        </observation>
        """
        result = classify_output(text)
        assert result.output_class == OutputClass.XML_DRIFT
        assert result.decision == BatchDecision.PRESERVE
        assert result.abort_reason == "drift:observer_schema"
    
    def test_idle_prose_no_observations(self):
        for text in [
            "No observations to record",
            "Nothing to observe at this time",
            "Ready and waiting for input",
            "Waiting for task",
        ]:
            result = classify_output(text)
            assert result.output_class == OutputClass.IDLE, f"Failed for: {text}"
            assert result.decision == BatchDecision.PRESERVE
    
    def test_prose_salvageable(self):
        text = "I noticed that the login flow has a bug where the token isn't validated properly. This could allow unauthorized access."
        result = classify_output(text)
        assert result.output_class == OutputClass.PROSE_SALVAGEABLE
        assert result.decision == BatchDecision.CONFIRM
        assert result.salvageable_content is not None
        assert len(result.salvageable_content) > 0
    
    def test_unclassified_prose_aborts(self):
        text = "Hello world, this is just some random text."
        result = classify_output(text)
        assert result.output_class == OutputClass.PROSE
        assert result.decision == BatchDecision.ABORT
        assert result.abort_reason == "prose:unclassified_output"


class TestTokenBudget:
    """Test token budget enforcement."""
    
    def test_estimate_tokens(self):
        assert estimate_tokens("hello") == 1  # 5 chars // 4 = 1
        assert estimate_tokens("hello world") == 2  # 11 chars // 4 = 2
        assert estimate_tokens("a" * 100) == 25
    
    def test_truncate_content(self):
        budget = TokenBudget()
        long_text = "a" * 10000
        truncated = budget.truncate_content(long_text, 100)
        assert len(truncated) <= 100
        assert "[truncated]" in truncated
    
    def test_no_truncate_when_under_limit(self):
        budget = TokenBudget()
        short_text = "hello world"
        result = budget.truncate_content(short_text, 100)
        assert result == short_text
    
    def test_truncate_history_under_budget(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        budget = TokenBudget(max_history_tokens=1000)
        result = truncate_history(history, budget)
        assert len(result) == 2
        assert result[0]["content"] == "Hello"
    
    def test_truncate_history_over_budget(self):
        history = [
            {"role": "user", "content": "a" * 10000},  # ~2500 tokens
            {"role": "assistant", "content": "b" * 10000},  # ~2500 tokens
            {"role": "user", "content": "c" * 10000},  # ~2500 tokens
        ]
        budget = TokenBudget(max_history_tokens=3000)
        result = truncate_history(history, budget)
        # Should keep only recent messages that fit
        assert len(result) <= 2
        total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in result)
        assert total_tokens <= budget.max_history_tokens
    
    def test_truncate_history_preserves_recent(self):
        history = [
            {"role": "user", "content": "old message " + "x" * 1000},
            {"role": "assistant", "content": "recent message"},
        ]
        budget = TokenBudget(max_history_tokens=100)
        result = truncate_history(history, budget)
        # Should keep the recent message
        assert any("recent" in msg.get("content", "") for msg in result)


class TestProcessModelOutput:
    """Test the main process_model_output function."""
    
    def test_process_valid_observation(self):
        text = '<observation><type>bugfix</type><title>Test</title><narrative>Details</narrative></observation>'
        result = process_model_output(text)
        assert result["classification"] == "valid"
        assert result["decision"] == "confirm"
        assert "observations" in result
    
    def test_process_idle_preserves_batch(self):
        text = "No observations to record"
        result = process_model_output(text)
        assert result["classification"] == "idle"
        assert result["decision"] == "preserve"
    
    def test_process_auth_preserves_batch(self):
        text = "Failed to authenticate 403"
        result = process_model_output(text)
        assert result["classification"] == "auth"
        assert result["decision"] == "preserve"
    
    def test_process_with_history(self):
        text = '<observation><type>bugfix</type><title>Test</title><narrative>Details</narrative></observation>'
        history = [
            {"role": "user", "content": "Previous message " + "x" * 5000},
            {"role": "assistant", "content": "Previous response " + "y" * 5000},
        ]
        budget = TokenBudget(max_history_tokens=1000)
        result = process_model_output(text, history=history, budget=budget)
        assert "history" in result
        assert "history_tokens" in result
        assert result["history_tokens"] <= budget.max_history_tokens
    
    def test_policy_table_complete(self):
        # Verify all output classes have a policy entry
        for output_class in OutputClass:
            assert output_class in POLICY_TABLE
            assert "decision" in POLICY_TABLE[output_class]
            assert POLICY_TABLE[output_class]["decision"] in BatchDecision


class TestIntegration:
    """Integration-style tests."""
    
    def test_full_workflow_valid_then_idle(self):
        # Simulate a session: valid observation, then idle
        history = []
        budget = TokenBudget(max_history_tokens=5000)
        
        # First turn: valid observation
        text1 = '<observation><type>bugfix</type><title>Fix bug</title><narrative>Fixed it</narrative></observation>'
        result1 = process_model_output(text1, history=history, budget=budget)
        assert result1["decision"] == "confirm"
        history = result1.get("history", [])
        
        # Add the assistant response to history
        history.append({"role": "assistant", "content": text1})
        
        # Second turn: idle
        text2 = "No observations to record"
        result2 = process_model_output(text2, history=history, budget=budget)
        assert result2["decision"] == "preserve"
    
    def test_overflow_triggers_history_reset(self):
        text = "Prompt is too long"
        history = [
            {"role": "user", "content": "x" * 20000},
            {"role": "assistant", "content": "y" * 20000},
        ]
        budget = TokenBudget(max_history_tokens=1000)
        result = process_model_output(text, history=history, budget=budget)
        assert result["classification"] == "overflow"
        assert result["decision"] == "preserve"
        # History should be truncated
        assert result["history_tokens"] <= budget.max_history_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
