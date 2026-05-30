"""
Execution service placeholder.

Future responsibility:
- create durable execution requests after approval
- assign idempotency keys
- call external billing provider adapters
- classify provider responses as success, transient failure, permanent failure, or unknown
- manage retry-safe execution states
- prevent duplicate money-impacting execution

Important product boundary:
Execution is deterministic and stateful. AI must never directly execute,
retry, or override money-impacting actions.
"""