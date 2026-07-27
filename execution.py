# execution.py
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from config import AutonomyTier, RiskLevel, RISK_POLICY, DEFAULT_AUTONOMY_TIER
from safety import GuardrailEngine, SafetyViolation
from audit import AuditStore
import tools as tool_catalog


class KillSwitch:
    def __init__(self):
        self._active = False
        self._reason: Optional[str] = None

    def activate(self, reason: str) -> None:
        self._active = True
        self._reason = reason

    def deactivate(self, actor: str) -> None:
        self._active = False
        self._reason = None

    def is_active(self) -> bool:
        return self._active

    @property
    def reason(self) -> Optional[str]:
        return self._reason


@dataclass
class ExecutionRequest:
    tool_name: str
    params: dict
    incident_id: str
    proposed_by: str
    justification: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)


@dataclass
class ExecutionResult:
    request_id: str
    status: str
    detail: str
    output: Optional[dict] = None


class RestrictedExecutor:
    def __init__(self, audit: AuditStore, guardrails: Optional[GuardrailEngine] = None,
                 kill_switch: Optional[KillSwitch] = None,
                 autonomy_tier: AutonomyTier = DEFAULT_AUTONOMY_TIER):
        self._audit = audit
        self._guardrails = guardrails or GuardrailEngine()
        self._kill_switch = kill_switch or KillSwitch()
        self._autonomy_tier = autonomy_tier
        self._pending: dict[str, ExecutionRequest] = {}

    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch

    def submit(self, request: ExecutionRequest) -> ExecutionResult:
        if self._kill_switch.is_active():
            result = ExecutionResult(
                request.request_id, "rejected",
                f"Kill switch active ({self._kill_switch.reason}). All execution halted.",
            )
            self._log("rejected", request, result)
            return result

        try:
            self._guardrails.full_precheck(request.tool_name, request.params, request.incident_id)
        except SafetyViolation as violation:
            result = ExecutionResult(request.request_id, "rejected", violation.message)
            self._log("refusal", request, result, extra={"violation_code": violation.code})
            return result

        spec = tool_catalog.get_tool(request.tool_name)
        policy = RISK_POLICY[spec.risk_level]

        if self._autonomy_tier < policy["min_tier"]:
            result = ExecutionResult(
                request.request_id, "rejected",
                f"Current autonomy tier ({self._autonomy_tier.name}) is below the tier required "
                f"for a {spec.risk_level.name}-risk action ({policy['min_tier'].name}).",
            )
            self._log("rejected", request, result)
            return result

        if policy["requires_approval"]:
            self._pending[request.request_id] = request
            result = ExecutionResult(
                request.request_id, "queued_for_approval",
                f"{spec.risk_level.name}-risk action '{request.tool_name}' requires human approval.",
            )
            self._log("queued_for_approval", request, result)
            return result

        return self._run(request, spec)

    def approve(self, request_id: str, approver: str) -> ExecutionResult:
        request = self._pending.pop(request_id, None)
        if request is None:
            raise ValueError(f"No pending request with id {request_id}")
        if self._kill_switch.is_active():
            result = ExecutionResult(request_id, "rejected", "Kill switch active; approval discarded.")
            self._log("rejected", request, result)
            return result
        spec = tool_catalog.get_tool(request.tool_name)
        result = self._run(request, spec)
        self._log("approved", request, result, extra={"approved_by": approver})
        return result

    def reject(self, request_id: str, rejector: str, reason: str) -> ExecutionResult:
        request = self._pending.pop(request_id, None)
        if request is None:
            raise ValueError(f"No pending request with id {request_id}")
        result = ExecutionResult(request_id, "rejected", f"Rejected by {rejector}: {reason}")
        self._log("rejected_by_human", request, result, extra={"rejected_by": rejector})
        return result

    def pending_approvals(self) -> tuple[ExecutionRequest, ...]:
        return tuple(self._pending.values())

    def set_autonomy_tier(self, tier: AutonomyTier, actor: str) -> None:
        self._audit.append(actor, "tier_change", {"new_tier": tier.name})
        self._autonomy_tier = tier

    def _run(self, request: ExecutionRequest, spec) -> ExecutionResult:
        try:
            output = spec.handler(**request.params)
        except Exception as exc:
            result = ExecutionResult(request.request_id, "rejected", f"Handler error: {exc}")
            self._log("execution_error", request, result)
            return result
        result = ExecutionResult(request.request_id, "executed", "Executed via whitelisted tool.", output)
        self._log("executed", request, result)
        return result

    def _log(self, event_type: str, request: ExecutionRequest, result: ExecutionResult, extra: dict | None = None):
        details = {
            "request_id": request.request_id,
            "incident_id": request.incident_id,
            "tool_name": request.tool_name,
            "params": request.params,
            "justification": request.justification,
            "result_status": result.status,
            "result_detail": result.detail,
        }
        if extra:
            details.update(extra)
        self._audit.append(request.proposed_by, event_type, details)