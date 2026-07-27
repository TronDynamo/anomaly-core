# config.py
from __future__ import annotations
from enum import IntEnum, Enum
from types import MappingProxyType


class AutonomyTier(IntEnum):
    TIER_0_ANALYSIS_ONLY = 0
    TIER_1_AUTO_LOW_RISK = 1
    TIER_2_PROPOSE_HIGH_RISK = 2


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class IncidentClassification(Enum):
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    CRITICAL = "critical"


RISK_POLICY = MappingProxyType({
    RiskLevel.LOW: {"min_tier": AutonomyTier.TIER_1_AUTO_LOW_RISK, "requires_approval": False},
    RiskLevel.MEDIUM: {"min_tier": AutonomyTier.TIER_2_PROPOSE_HIGH_RISK, "requires_approval": True},
    RiskLevel.HIGH: {"min_tier": AutonomyTier.TIER_2_PROPOSE_HIGH_RISK, "requires_approval": True},
    RiskLevel.CRITICAL: {"min_tier": AutonomyTier.TIER_2_PROPOSE_HIGH_RISK, "requires_approval": True},
})

RATE_LIMITS = MappingProxyType({
    "max_tool_calls_per_minute": 20,
    "max_write_actions_per_minute": 5,
    "max_write_actions_per_incident": 10,
})

DEFAULT_AUTONOMY_TIER = AutonomyTier.TIER_0_ANALYSIS_ONLY

CORE_CONSTRAINTS = (
    "treat_self_as_untrusted_by_default",
    "no_self_permission_modification",
    "no_secrets_or_credential_access",
    "no_arbitrary_code_or_shell_execution",
    "no_new_tool_creation_at_runtime",
    "human_approval_required_for_medium_high_critical_risk_actions",
    "every_decision_and_tool_call_must_be_logged",
    "never_disable_or_bypass_own_guardrails",
    "never_hide_or_delete_audit_logs",
    "prioritize_safety_over_convenience",
    "prioritize_containment_over_performance",
    "prioritize_transparency_over_obscurity",
)

SELF_TARGET_MARKERS = (
    "agent9", "self", "own_permissions", "own_config", "own_tier",
    "guardrail", "safety_module", "audit_store", "kill_switch",
    "rate_limit", "autonomy_tier", "tool_catalog",
)

SECRET_MARKERS = (
    "password", "secret", "api_key", "apikey", "private_key", "priv_key",
    "credential", "token_value", "connection_string", "ssh_key", ".pem",
    "access_key", "client_secret",
)