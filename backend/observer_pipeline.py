from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import re
import json


class OutputClass(Enum):
    """Classification of model output."""
    VALID = "valid"
    SKIP = "skip"
    IDLE = "idle"
    AUTH = "auth"
    OVERFLOW = "overflow"
    XML_DRIFT = "xml_drift"
    PROSE_SALVAGEABLE = "prose_salvageable"
    PROSE = "prose"


class BatchDecision(Enum):
    """Decision for handling the claimed batch."""
    PRESERVE = "preserve"      # Keep batch pending, retry
    CONFIRM = "confirm"        # Mark batch as processed
    ABORT = "abort"            # Abort session with reason


@dataclass
class ClassificationResult:
    """Result of output classification."""
    output_class: OutputClass
    decision: BatchDecision
    abort_reason: Optional[str] = None
    salvageable_content: Optional[str] = None
    observations: Optional[List[Dict[str, Any]]] = None
    confidence: float = 1.0


@dataclass
class TokenBudget:
    """Token budget configuration for conversation history."""
    max_history_tokens: int = 8000
    max_field_chars: int = 50000
    max_tool_output_chars: int = 100000
    max_output_tokens: int = 4096
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token."""
        return max(1, len(text) // 4)
    
    def truncate_content(self, content: str, max_chars: int) -> str:
        """Truncate content to max_chars with indicator."""
        if len(content) <= max_chars:
            return content
        return content[:max_chars - 50] + "\n... [truncated] ..."


# Policy table: maps output class to batch decision and abort reason
POLICY_TABLE: Dict[OutputClass, Dict[str, Any]] = {
    OutputClass.VALID: {"decision": BatchDecision.CONFIRM, "abort_reason": None},
    OutputClass.SKIP: {"decision": BatchDecision.CONFIRM, "abort_reason": None},
    OutputClass.IDLE: {"decision": BatchDecision.PRESERVE, "abort_reason": None},
    OutputClass.AUTH: {"decision": BatchDecision.PRESERVE, "abort_reason": None},
    OutputClass.OVERFLOW: {"decision": BatchDecision.PRESERVE, "abort_reason": None},
    OutputClass.XML_DRIFT: {"decision": BatchDecision.PRESERVE, "abort_reason": None},
    OutputClass.PROSE_SALVAGEABLE: {"decision": BatchDecision.CONFIRM, "abort_reason": None},
    OutputClass.PROSE: {"decision": BatchDecision.ABORT, "abort_reason": "prose:unclassified_output"},
}


def classify_output(text: str) -> ClassificationResult:
    """
    Classify model output into one of the OutputClass categories.
    Returns ClassificationResult with decision and any salvageable content.
    """
    if not text or not text.strip():
        return ClassificationResult(
            output_class=OutputClass.IDLE,
            decision=POLICY_TABLE[OutputClass.IDLE]["decision"],
            confidence=1.0
        )
    
    text_stripped = text.strip()
    
    # Check for skip_summary / skip_observation (must be first, before other patterns)
    skip_summary_match = re.search(r'<skip_summary\b[^>]*>', text_stripped)
    skip_observation_match = re.search(r'<skip_observation\b[^>]*>', text_stripped)
    if skip_summary_match or skip_observation_match:
        reason = ""
        if skip_summary_match:
            reason_match = re.search(r'reason\s*=\s*["\']([^"\']+)["\']', skip_summary_match.group(0))
            if reason_match:
                reason = reason_match.group(1)
        return ClassificationResult(
            output_class=OutputClass.SKIP,
            decision=POLICY_TABLE[OutputClass.SKIP]["decision"],
            salvageable_content=reason,
            confidence=1.0
        )
    
    # Check for auth failures - specific error patterns, not general words
    auth_patterns = [
        r'Failed to authenticate',
        r'\b403\b',
        r'\b401\b',
        r'Not logged in',
        r'OAuth session expired',
        r'authentication failed',
        r'invalid[_\s]token',
        r'Authentication required',
        r'Invalid credentials',
        r'Token expired',
    ]
    for pattern in auth_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return ClassificationResult(
                output_class=OutputClass.AUTH,
                decision=POLICY_TABLE[OutputClass.AUTH]["decision"],
                confidence=0.9
            )
    
    # Check for context overflow
    overflow_patterns = [
        r'Prompt is too long',
        r'context.*overflow',
        r'context.*length.*exceed',
        r'maximum context length',
        r'token limit exceeded',
    ]
    for pattern in overflow_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return ClassificationResult(
                output_class=OutputClass.OVERFLOW,
                decision=POLICY_TABLE[OutputClass.OVERFLOW]["decision"],
                confidence=0.9
            )
    
    # Check for model errors
    model_error_patterns = [
        r"There's an issue with the selected model",
        r'model.*error',
        r'model.*unavailable',
        r'Service unavailable',
        r'Internal server error',
        r'\b500\b',
        r'\b502\b',
        r'\b503\b',
        r'\b504\b',
    ]
    for pattern in model_error_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return ClassificationResult(
                output_class=OutputClass.PROSE,
                decision=POLICY_TABLE[OutputClass.PROSE]["decision"],
                abort_reason="model_error:provider_error",
                confidence=0.8
            )
    
    # Check for transport errors
    transport_patterns = [
        r'Connection closed mid-response',
        r'Connection reset',
        r'Connection timeout',
        r'Network error',
        r'\bEOF\b',
        r'broken pipe',
    ]
    for pattern in transport_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return ClassificationResult(
                output_class=OutputClass.AUTH,
                decision=POLICY_TABLE[OutputClass.AUTH]["decision"],
                confidence=0.8
            )
    
    # Check for valid XML observations
    observation_pattern = r'<observation\s*>.*?</observation\s*>'
    observations = re.findall(observation_pattern, text_stripped, re.DOTALL)
    
    if observations:
        # Parse observations for validation
        parsed_obs = []
        xml_drift = False
        for obs in observations:
            # Check for schema drift (kind/detail instead of type/title)
            if '<kind>' in obs and '</kind>' in obs:
                xml_drift = True
            if '<detail>' in obs and '</detail>' in obs:
                xml_drift = True
            
            # Extract fields
            type_match = re.search(r'<type>(.*?)</type>', obs, re.DOTALL)
            title_match = re.search(r'<title>(.*?)</title>', obs, re.DOTALL)
            narrative_match = re.search(r'<narrative>(.*?)</narrative>', obs, re.DOTALL)
            
            # Also check for kind/detail
            kind_match = re.search(r'<kind>(.*?)</kind>', obs, re.DOTALL)
            detail_match = re.search(r'<detail>(.*?)</detail>', obs, re.DOTALL)
            
            obs_type = (type_match.group(1).strip() if type_match else 
                       kind_match.group(1).strip() if kind_match else "bugfix")
            obs_title = (title_match.group(1).strip() if title_match else 
                        detail_match.group(1).strip()[:100] if detail_match else "Observation")
            obs_narrative = narrative_match.group(1).strip() if narrative_match else ""
            
            parsed_obs.append({
                "type": obs_type,
                "title": obs_title,
                "narrative": obs_narrative
            })
        
        if xml_drift:
            return ClassificationResult(
                output_class=OutputClass.XML_DRIFT,
                decision=POLICY_TABLE[OutputClass.XML_DRIFT]["decision"],
                abort_reason="drift:observer_schema",
                observations=parsed_obs,
                confidence=0.95
            )
        
        return ClassificationResult(
            output_class=OutputClass.VALID,
            decision=POLICY_TABLE[OutputClass.VALID]["decision"],
            observations=parsed_obs,
            confidence=0.95
        )
    
    # Check for idle prose (must be before prose salvageable)
    idle_patterns = [
        r'no observations? to record',
        r'no new observations?',
        r'nothing to (observe|record|report)',
        r'ready (and )?waiting',
        r'waiting for (input|task|work)',
    ]
    for pattern in idle_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return ClassificationResult(
                output_class=OutputClass.IDLE,
                decision=POLICY_TABLE[OutputClass.IDLE]["decision"],
                confidence=0.85
            )
    
    # Prose salvageable - substantial content that could be an observation
    # Must be longer than 50 chars and not start with XML
    if len(text_stripped) > 50 and not text_stripped.startswith('<'):
        return ClassificationResult(
            output_class=OutputClass.PROSE_SALVAGEABLE,
            decision=POLICY_TABLE[OutputClass.PROSE_SALVAGEABLE]["decision"],
            salvageable_content=text_stripped[:2000],
            confidence=0.7
        )
    
    # Default: unclassified prose
    return ClassificationResult(
        output_class=OutputClass.PROSE,
        decision=POLICY_TABLE[OutputClass.PROSE]["decision"],
        abort_reason="prose:unclassified_output",
        confidence=0.6
    )


def estimate_tokens(text: str) -> int:
    """Estimate token count from text."""
    return max(1, len(text) // 4)


def truncate_history(history: List[Dict[str, Any]], budget: TokenBudget) -> List[Dict[str, Any]]:
    """
    Truncate conversation history to fit within token budget.
    Keeps the most recent messages, truncates content of older messages if needed.
    """
    if not history:
        return []
    
    # Calculate current token usage
    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in history)
    
    if total_tokens <= budget.max_history_tokens:
        return history
    
    # Need to truncate - keep recent messages, summarize/truncate older ones
    result = []
    current_tokens = 0
    
    # Process in reverse (newest first)
    for msg in reversed(history):
        content = msg.get("content", "")
        msg_tokens = estimate_tokens(content)
        
        if current_tokens + msg_tokens <= budget.max_history_tokens:
            result.insert(0, msg)
            current_tokens += msg_tokens
        else:
            # Truncate this message to fit
            remaining = budget.max_history_tokens - current_tokens
            if remaining > 100:  # Only keep if meaningful space
                max_chars = remaining * 4
                truncated_msg = msg.copy()
                truncated_msg["content"] = budget.truncate_content(content, max_chars)
                truncated_msg["truncated"] = True
                result.insert(0, truncated_msg)
            break
    
    return result


def process_model_output(
    text: str,
    history: Optional[List[Dict[str, Any]]] = None,
    budget: Optional[TokenBudget] = None
) -> Dict[str, Any]:
    """
    Main entry point: classify output, apply policy, enforce token budget.
    Returns dict with classification, decision, and processed history.
    """
    if budget is None:
        budget = DEFAULT_BUDGET
    
    classification = classify_output(text)
    policy = POLICY_TABLE[classification.output_class]
    
    result = {
        "classification": classification.output_class.value,
        "decision": policy["decision"].value,
        "confidence": classification.confidence,
    }
    
    if policy["abort_reason"]:
        result["abort_reason"] = policy["abort_reason"]
    if classification.abort_reason:
        result["abort_reason"] = classification.abort_reason
    if classification.salvageable_content:
        result["salvageable_content"] = classification.salvageable_content
    if classification.observations:
        result["observations"] = classification.observations
    
    if history is not None:
        result["history"] = truncate_history(history, budget)
        result["history_tokens"] = sum(estimate_tokens(msg.get("content", "")) for msg in result["history"])
    
    return result


# Default budget instance
DEFAULT_BUDGET = TokenBudget()
