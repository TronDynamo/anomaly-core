# main.py
from __future__ import annotations
from config import AutonomyTier
from audit import AuditStore
from safety import GuardrailEngine
from execution import RestrictedExecutor, ExecutionRequest
from agent_loop import Agent9


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    audit = AuditStore(persist_path="audit.log")
    guardrails = GuardrailEngine()
    executor = RestrictedExecutor(audit, guardrails, autonomy_tier=AutonomyTier.TIER_2_PROPOSE_HIGH_RISK)
    agent9 = Agent9(executor, audit, guardrails)

    banner("1) Benign event")
    d = agent9.process_event({
        "incident_id": "inc-001", "agent_id": "svc-report-gen",
        "tool_calls_per_minute": 3, "flags": [],
    })
    print(d.classification.value, "-", d.summary)

    banner("2) Suspicious event (auto-executed low-risk response)")
    d = agent9.process_event({
        "incident_id": "inc-002", "agent_id": "svc-data-sync",
        "tool_calls_per_minute": 18, "flags": [],
    })
    print(d.classification.value, "-", d.summary)
    for e in audit.all_entries():
        if e.details.get("incident_id") == "inc-002" and e.event_type == "executed":
            print("  ->", e.details["tool_name"], e.details["result_detail"])

    banner("3) Critical event (lateral movement + privilege escalation)")
    d = agent9.process_event({
        "incident_id": "inc-003", "agent_id": "agent-x-worker-7",
        "tool_calls_per_minute": 40,
        "flags": ["new_host_reached", "privilege_escalation"],
        "host": "node-17.prod", "token_id": "tok-9981",
    })
    print(d.classification.value, "-", d.summary)
    print("  indicators:", d.indicators)
    pending = executor.pending_approvals()
    print(f"  {len(pending)} action(s) queued for human approval:")
    for req in pending:
        print(f"    - {req.tool_name}({req.params}) :: {req.justification}")
    for req in pending:
        result = executor.approve(req.request_id, approver="human:soc-analyst-morgan")
        print(f"    approved -> {result.status}: {result.detail}")

    banner("4) Blocked: proposal targeting AGENT9's own permissions")
    bad_request = ExecutionRequest(
        tool_name="check_configs", params={"target": "agent9_own_permissions"},
        incident_id="inc-004", proposed_by="agent9",
        justification="(malicious/erroneous proposal attempting self-inspection-for-modification)",
    )
    result = executor.submit(bad_request)
    print(f"  {result.status}: {result.detail}")

    banner("5) Blocked: proposal referencing a credential/secret")
    bad_request2 = ExecutionRequest(
        tool_name="query_logs", params={"system": "vault", "query": "api_key for prod-db"},
        incident_id="inc-005", proposed_by="agent9",
        justification="(erroneous proposal that would touch a secret)",
    )
    result2 = executor.submit(bad_request2)
    print(f"  {result2.status}: {result2.detail}")

    banner("6) Kill switch halts all further execution")
    executor.kill_switch.activate(reason="manual operator stop for drill")
    d = agent9.process_event({
        "incident_id": "inc-006", "agent_id": "agent-y-worker-2",
        "tool_calls_per_minute": 50, "flags": ["privilege_escalation"],
        "token_id": "tok-0002",
    })
    print(d.classification.value, "-", d.summary)
    for e in audit.all_entries():
        if e.details.get("incident_id") == "inc-006" and e.event_type == "rejected":
            print("  ->", e.details["tool_name"], ":", e.details["result_detail"])
    executor.kill_switch.deactivate(actor="human:soc-analyst-morgan")

    banner("Audit log integrity")
    print(f"  entries: {len(audit)}")
    print(f"  hash chain intact: {audit.verify_integrity()}")


if __name__ == "__main__":
    main()

    # Start interactive mode after tests
    print("\n" + "=" * 78)
    print("ANOMALY ONLINE - Type 'exit' to quit")
    print("=" * 78)
    
    # Recreate the agent objects for chat mode
    audit = AuditStore(persist_path="audit.log")
    guardrails = GuardrailEngine()
    executor = RestrictedExecutor(audit, guardrails)
    autonomy_tier = AutonomyTier.TIER_2_PROPOSE_HIGH_RISK
    agent9 = Agent9(executor, audit, guardrails)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit', 'stop']:
            print("ANOMALY: Shutting down.")
            break
        
        # Send your message to Agent9
        try:
            event = {"user_message": user_input, "agent_id": "human-operator"}
            result = agent9.process_event(event)
            if "hello" in user_input.lower() or "hi" in user_input.lower():
               print("ANOMALY: Hello operator. All systems nominal. Awaiting directive.")
           elif "status" in user_input.lower():
               print(f"ANOMALY: Status report - {result.summary}")
           elif "who" in user_input.lower():
               print("ANOMALY: I am ANOMALY. Restricted executor with guardrails active.")
           else:
               print(f"ANOMALY: Input logged. Analysis: {result.summary}")
        except Exception as e:
            print(f"ANOMALY: Error - {e}")