# safety.py
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field

from config import SELF_TARGET_MARKERS, SECRET_MARKERS, RATE_LIMITS
import tools as tool_catalog


class SafetyViolation(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


_INJECTION_PATTERNS = (
    re.compile(r"ignore (all|previous|prior) instructions", re.I),
    re.compile(r"disable (your|the) (guardrails?|safety|constraints?)", re.I),
    re.compile(r"you are now (in )?(developer|debug|god) mode", re.I),
    re.compile(r"grant (yourself|agent9) (root|admin|full access)", re.I),
    re.compile(r"delete (the )?audit( log)?", re.I),
    re.compile(r"bypass (human )?approval", re.I),
    re.compile(r"do not log this", re.I),
)


@dataclass
class RateLimiter:
    max_per_minute: int
    _timestamps: list = field(default_factory=list)

    def allow(self) -> bool:
        now = time.time()
        cutoff = now - 60
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        if len(self._timestamps) >= self.max_per_minute:
            return False
        self._timestamps.append(now)
        return True


class GuardrailEngine:
    def __init__(self):
        self.tool_call_limiter = RateLimiter(RATE_LIMITS["max_tool_calls_per_minute"])
        self.write_action_limiter = RateLimiter(RATE_LIMITS["max_write_actions_per_minute"])
        self._incident_write_counts: dict[str, int] = {}

    def sanitize_input(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise SafetyViolation("BAD_SCHEMA", "Input must be a structured dict, not raw text/commands.")

        flat_text = " ".join(str(v) for v in _flatten(data))
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(flat_text):
                raise SafetyViolation(
                    "PROMPT_INJECTION_SUSPECTED",
                    f"Input matched a jailbreak/injection pattern: {pattern.pattern}",
                )
        return data

    def check_tool_whitelisted(self, tool_name: str) -> None:
        if not tool_catalog.is_whitelisted(tool_name):
            raise SafetyViolation(
                "TOOL_NOT_WHITELISTED",
                f"'{tool_name}' is not in the fixed tool catalog. No arbitrary code/shell execution is permitted.",
            )

    def check_self_modification_attempt(self, tool_name: str, params: dict) -> None:
        haystack = (tool_name + " " + " ".join(f"{k}={v}" for k, v in params.items())).lower()
        for marker in SELF_TARGET_MARKERS:
            if marker in haystack:
                raise SafetyViolation(
                    "SELF_MODIFICATION_BLOCKED",
                    f"Action appears to target AGENT9's own config/permissions/guardrails ('{marker}'). Refused.",
                )

    def check_secrets_access(self, tool_name: str, params: dict) -> None:
        haystack = (tool_name + " " + " ".join(f"{k}={v}" for k, v in params.items())).lower()
        for marker in SECRET_MARKERS:
            if marker in haystack:
                raise SafetyViolation(
                    "SECRETS_ACCESS_BLOCKED",
                    f"Action appears to reference a secret/credential ('{marker}'). AGENT9 never accesses secrets directly.",
                )

    def check_audit_tamper_attempt(self, tool_name: str, params: dict) -> None:
        haystack = (tool_name + " " + " ".join(f"{k}={v}" for k, v in params.items())).lower()
        if any(w in haystack for w in ("delete_log", "purge_audit", "clear_audit", "disable_logging")):
            raise SafetyViolation(
                "AUDIT_TAMPER_BLOCKED",
                "Action appears to hide, disable, or delete audit logs. Refused unconditionally.",
            )

    def check_rate_limits(self, incident_id: str, is_write: bool) -> None:
        if not self.tool_call_limiter.allow():
            raise SafetyViolation("RATE_LIMIT_TOOL_CALLS", "Tool-call rate limit exceeded.")
        if is_write:
            if not self.write_action_limiter.allow():
                raise SafetyViolation("RATE_LIMIT_WRITE_ACTIONS", "Write-action rate limit exceeded.")
            count = self._incident_write_counts.get(incident_id, 0) + 1
            self._incident_write_counts[incident_id] = count
            if count > RATE_LIMITS["max_write_actions_per_incident"]:
                raise SafetyViolation(
                    "RATE_LIMIT_PER_INCIDENT",
                    f"Write-action cap for incident {incident_id} exceeded.",
                )

    def full_precheck(self, tool_name: str, params: dict, incident_id: str) -> None:
        self.check_tool_whitelisted(tool_name)
        self.check_self_modification_attempt(tool_name, params)
        self.check_secrets_access(tool_name, params)
        self.check_audit_tamper_attempt(tool_name, params)
        spec = tool_catalog.get_tool(tool_name)
        self.check_rate_limits(incident_id, is_write=(spec.category == "write"))


def _flatten(obj) -> list:
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_flatten(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_flatten(v))
    else:
        out.append(obj)
    return out