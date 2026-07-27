# ANOMALY ("Morals AI")

Defensive AI agent that detects, analyzes, and helps contain rogue AI
agent behavior, structurally prevented from going rogue itself.

## Files

- `config.py` — immutable constants: autonomy tiers, risk policy, rate
  limits, core "Morals AI" constraints, self-target/secret marker lists.
- `audit.py` — append-only, hash-chained `AuditStore`. No delete/edit
  method exists; `verify_integrity()` detects tampering.
- `tools.py` — the fixed tool catalog (`TOOL_CATALOG`). This is AGENT9's
  entire action space — read tools (query logs, check configs, list
  sessions, network telemetry, model activity traces) and pre-approved
  write/containment tools (revoke token, isolate host, disable session,
  block IP, increase logging). No "run shell" / "eval" tool exists, and
  none can be added at runtime.
- `safety.py` — `GuardrailEngine`: input sanitization + prompt-injection
  screening, tool-whitelist enforcement, self-modification blocking,
  secrets-access blocking, audit-tamper blocking, rate limiting.
- `execution.py` — `RestrictedExecutor` + `KillSwitch`. The only place
  tool handlers are actually invoked. Enforces guardrails, autonomy
  tiers, and the human-approval queue before any write action runs.
- `agent_loop.py` — `Agent9`: ingest → sanitize → classify (benign /
  suspicious / critical) → explain → propose playbooks → submit each
  proposal to the executor. The heuristic reasoner is a pluggable hook
  (`ReasonerFn`) so a real Claude-backed reasoning call can be swapped in
  without touching the guardrail or execution layers.
- `main.py` — runnable demo covering all six safeguards end to end.

## Run the demo

```
python3 main.py
```

## Safety model at a glance

- **Untrusted by default**: Anomaly's own proposals are re-checked by the
  same guardrails as external input, not just tool outputs.
- **Autonomy ceiling**: Tier 2 is the maximum tier — auto-execute
  low-risk actions, propose (never auto-run) medium/high/critical-risk
  actions. There is no tier that grants unapproved high-impact execution.
- **Kill switch**: `executor.kill_switch.activate(reason)` halts all
  execution instantly, including anything already queued for approval.
- **Everything is logged**: every decision, proposal, execution,
  approval, rejection, and refusal is written to the hash-chained audit
  store before control returns to the caller.

## Wiring in real infrastructure / a real model

- Swap the simulated handler bodies in `tools.py` for real SIEM/IAM/
  network API calls — the catalog shape, risk levels, and guardrails
  don't need to change.
- Pass a `reasoner` callable into `Anomaly(...)` that calls the Claude API
  with a structured, schema-constrained prompt instead of
  `default_heuristic_reasoner`. Its output still flows through the exact
  same `GuardrailEngine` and `RestrictedExecutor` — model output is never
  trusted more than a heuristic's output.
