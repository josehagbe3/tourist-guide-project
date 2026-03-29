from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


# -----------------------------
# ENUMS (controlled states)
# -----------------------------

class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    EMPTY = "empty"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# -----------------------------
# USER INTENT
# -----------------------------

@dataclass
class UserIntent:
    """
    Represents structured understanding of user input.

    Why this matters:
    - Separates language from logic
    - Prevents downstream guessing
    """
    destination: Optional[str]
    date: Optional[str]
    num_days: Optional[int]
    budget: Optional[float]
    from_currency: Optional[str]   # currency the budget is expressed in
    to_currency: Optional[str]     # currency to display converted costs in


# -----------------------------
# PLANNER OUTPUT
# -----------------------------

@dataclass
class Plan:
    """
    Decision layer output.

    Must explicitly answer:
    - Do we proceed?
    - What is missing?
    - Which tools to call?
    """
    requires_clarification: bool
    missing_fields: List[str]
    tools_to_call: List[str]
    reasoning: str


# -----------------------------
# TOOL RESULT
# -----------------------------

@dataclass
class ToolResult:
    """
    Standardized output of ANY tool.

    Why:
    - All tools behave consistently
    - Executor + Validator can reason safely
    """
    tool_name: str
    status: ToolStatus
    data: Optional[Dict[str, Any]]
    error_message: Optional[str]


# -----------------------------
# VALIDATION OUTPUT
# -----------------------------

@dataclass
class ValidationResult:
    """
    Post-tool reasoning layer.

    This is where the system 'thinks about' data quality.
    """
    normalized_data: Dict[str, Any]
    constraints: List[str]   # e.g. "weather_unavailable"
    confidence: ConfidenceLevel
    issues: List[str]


# -----------------------------
# FINAL RESPONSE PACKAGE
# -----------------------------

@dataclass
class AgentResponse:
    """
    Final structured output returned to UI / API.

    CRITICAL for your frontend and evaluation.
    """
    response_text: str
    planner_info: str
    tool_outputs: Dict[str, Any]
    confidence: ConfidenceLevel
    errors: List[str]