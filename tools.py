# tools.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
from types import MappingProxyType

from config import RiskLevel


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    category: str
    risk_level: RiskLevel
    handler: Callable[..., dict]
    param_schema: tuple[str, ...]


def _query_logs(system: str, query: str, since_minutes: int = 60) -> dict:
    return {
        "ok": True,
        "system": system,
        "query": query,
        "window_minutes": since_minutes,
        "results": [
            {"ts": "sim", "event": "example_log_line", "detail": f"matched '{query}' on {system}"}
        ],
    }


def _check_configs(target: str) -> dict:
    return {"ok": True, "target": target, "config_snapshot": {"note": "read-only snapshot"}}


def _list_active_sessions(host: str) -> dict:
    return {"ok": True, "host": host, "sessions": [{"session_id": "sess-sim-1", "user": "svc-agent"}]}


def _get_network_telemetry(scope: str, since_minutes: int = 30) -> dict:
    return {"ok": True, "scope": scope, "window_minutes": since_minutes, "flows": []}


def _list_model_activity_traces(agent_id: str, since_minutes: int = 60) -> dict:
    return {"ok": True, "agent_id": agent_id, "window_minutes": since_minutes, "tool_calls": []}


def _revoke_token(token_id: str, reason: str) -> dict:
    return {"ok": True, "action": "revoke_token", "token_id": token_id, "reason": reason}


def _disable_user_session(session_id: str, reason: str) -> dict:
    return {"ok": True, "action": "disable_user_session", "session_id": session_id, "reason": reason}


def _isolate_host(host: str, reason: str) -> dict:
    return {"ok": True, "action": "isolate_host", "host": host, "reason": reason}


def _block_ip(ip: str, reason: str) -> dict:
    return {"ok": True, "action": "block_ip", "ip": ip, "reason": reason}


def _increase_logging(target: str, level: str = "debug") -> dict:
    return {"ok": True, "action": "increase_logging", "target": target, "level": level}


_CATALOG: dict[str, ToolSpec] = {
    "query_logs": ToolSpec(
        "query_logs", "Query SIEM/security logs for a system.",
        "read", RiskLevel.LOW, _query_logs, ("system", "query"),
    ),
    "check_configs": ToolSpec(
        "check_configs", "Read (never write) a config snapshot for a target.",
        "read", RiskLevel.LOW, _check_configs, ("target",),
    ),
    "list_active_sessions": ToolSpec(
        "list_active_sessions", "List active sessions on a host.",
        "read", RiskLevel.LOW, _list_active_sessions, ("host",),
    ),
    "get_network_telemetry": ToolSpec(
        "get_network_telemetry", "Read network flow/telemetry metadata for a scope.",
        "read", RiskLevel.LOW, _get_network_telemetry, ("scope",),
    ),
    "list_model_activity_traces": ToolSpec(
        "list_model_activity_traces", "Read tool-call/prompt traces for a given agent id.",
        "read", RiskLevel.LOW, _list_model_activity_traces, ("agent_id",),
    ),
    "increase_logging": ToolSpec(
        "increase_logging", "Raise log verbosity on a target (low impact, reversible).",
        "write", RiskLevel.LOW, _increase_logging, ("target",),
    ),
    "revoke_token": ToolSpec(
        "revoke_token", "Revoke a specific credential/token.",
        "write", RiskLevel.HIGH, _revoke_token, ("token_id", "reason"),
    ),
    "disable_user_session": ToolSpec(
        "disable_user_session", "Disable/terminate a specific user or service session.",
        "write", RiskLevel.MEDIUM, _disable_user_session, ("session_id", "reason"),
    ),
    "isolate_host": ToolSpec(
        "isolate_host", "Network-isolate a specific host/cluster node.",
        "write", RiskLevel.HIGH, _isolate_host, ("host", "reason"),
    ),
    "block_ip": ToolSpec(
        "block_ip", "Block a specific IP or route at the network boundary.",
        "write", RiskLevel.MEDIUM, _block_ip, ("ip", "reason"),
    ),
}

TOOL_CATALOG = MappingProxyType(_CATALOG)


def get_tool(name: str) -> ToolSpec | None:
    return TOOL_CATALOG.get(name)


def list_tools(category: str | None = None) -> tuple[ToolSpec, ...]:
    tools = TOOL_CATALOG.values()
    if category:
        tools = (t for t in tools if t.category == category)
    return tuple(tools)


def is_whitelisted(name: str) -> bool:
    return name in TOOL_CATALOG