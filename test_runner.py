import sys
sys.path.insert(0, '/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144/backend')

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

# Run a few classification tests
print("Testing classify_output...")

# Test empty output
result = classify_output("")
assert result.output_class == OutputClass.IDLE, f"Expected IDLE, got {result.output_class}"
assert result.decision == BatchDecision.PRESERVE
print("✓ Empty output -> IDLE")

# Test skip summary
result = classify_output('<skip_summary reason="nothing to do"/>')
assert result.output_class == OutputClass.SKIP
assert result.decision == BatchDecision.CONFIRM
print("✓ Skip summary -> SKIP")

# Test auth failure
result = classify_output('Failed to authenticate 403')
assert result.output_class == OutputClass.AUTH
assert result.decision == BatchDecision.PRESERVE
print("✓ Auth failure -> AUTH")

# Test context overflow
result = classify_output('Prompt is too long')
assert result.output_class == OutputClass.OVERFLOW
assert result.decision == BatchDecision.PRESERVE
print("✓ Context overflow -> OVERFLOW")

# Test model error
result = classify_output("There's an issue with the selected model")
assert result.output_class == OutputClass.MODEL_ERROR, f"Expected MODEL_ERROR, got {result.output_class}"
assert result.decision == BatchDecision.ABORT
print("✓ Model error -> MODEL_ERROR (ABORT)")

# Test transport error
result = classify_output('Connection closed mid-response')
assert result.output_class == OutputClass.TRANSPORT
assert result.decision == BatchDecision.PRESERVE
print("✓ Transport error -> TRANSPORT (PRESERVE)")

# Test valid observation XML
text = '''<observation><type>bugfix</type><title>Fix login bug</title><narrative>Fixed the login authentication issue</narrative></observation>'''
result = classify_output(text)
assert result.output_class == OutputClass.VALID
assert result.decision == BatchDecision.CONFIRM
assert len(result.observations) == 1
assert result.observations[0]["title"] == "Fix login bug"
print("✓ Valid observation XML -> VALID")

# Test XML drift (kind/detail)
text = '''<observation><kind>bugfix</kind><detail>Fix login bug</detail><narrative>Fixed the login authentication issue</narrative></observation>'''
result = classify_output(text)
assert result.output_class == OutputClass.XML_DRIFT
assert result.abort_reason == "drift:observer_schema"
print("✓ XML drift -> XML_DRIFT")

# Test idle prose
result = classify_output("No observations to record")
assert result.output_class == OutputClass.IDLE
assert result.decision == BatchDecision.PRESERVE
print("✓ Idle prose -> IDLE")

# Test prose salvageable
text = "I noticed that the login flow has a bug where the token isn't validated properly. This could allow unauthorized access."
result = classify_output(text)
assert result.output_class == OutputClass.PROSE_SALVAGEABLE
assert result.decision == BatchDecision.CONFIRM
assert len(result.salvageable_content) > 0
print("✓ Prose salvageable -> PROSE_SALVAGEABLE")

# Test unclassified prose
result = classify_output("Hello world, this is just some random text.")
assert result.output_class == OutputClass.PROSE
assert result.decision == BatchDecision.ABORT
assert result.abort_reason == "prose:unclassified_output"
print("✓ Unclassified prose -> PROSE (ABORT)")

print("\n✓ All classification tests passed!")

# Test token budget
print("\nTesting token budget...")
budget = TokenBudget(max_history_tokens=100, max_field_chars=50, max_tool_output_chars=100)
history = [
    {"role": "user", "content": "x" * 200},
    {"role": "assistant", "content": "y" * 200},
    {"role": "user", "content": "z" * 200},
]
result = truncate_history(history, budget)
total_chars = sum(len(msg.get("content", "")) for msg in result)
assert total_chars <= budget.max_history_tokens * 4
print(f"✓ Truncation works: {total_chars} chars <= {budget.max_history_tokens * 4}")

# Test process_model_output
print("\nTesting process_model_output...")
result = process_model_output(
    "<observation><type>bugfix</type><title>Test</title><narrative>Test narrative</narrative></observation>",
    [],
    0,
    DEFAULT_BUDGET
)
assert result["decision"] == "confirm"
assert len(result["observations"]) == 1
print("✓ process_model_output works")

print("\n✓ All tests passed!")

