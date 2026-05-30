# Billing Recovery Execution Console

A portfolio project demonstrating how a billing operations system can move from human-approved billing corrections to reliable execution, retry handling, reconciliation, and manual recovery.

## Product Thesis

Billing corrections are not complete when a human approves them. They are complete only when the approved action is safely executed, verified against the external billing provider, reconciled with internal state, and recoverable when execution fails.

## Why This Project Exists

This project is part of a product portfolio focused on realistic working systems rather than coding demos.

Previous projects explored:

* AI-assisted decision support
* human-in-the-loop operational workflows
* product-grade operations UX
* external dependency awareness

This project focuses on the next progression:

> reliable execution after human approval.

The goal is to model what happens when an approved operational decision must become a safe, durable, auditable action against an external system.

## Current Implementation

The current implementation supports:

- seeded billing correction cases
- billing work queue
- case detail view
- deterministic policy evaluation
- persisted policy outcomes
- human approval and rejection capture
- role-aware approval validation
- approval rationale capture
- durable execution request creation
- deterministic idempotency key generation
- duplicate execution request prevention
- mock provider execution
- execution attempt tracking
- provider success, transient failure, permanent failure, and timeout simulation
- execution status transitions after provider response
- retry eligibility evaluation
- manual retry for transient execution failures
- maximum retry limit
- retry attempt tracking
- automatic movement to manual review after retry limit is reached
- reconciliation against mock provider source of truth
- reconciliation history
- matched success detection
- matched failure detection
- mismatch detection
- routing unsafe mismatches to manual review
- manual recovery workflow for unresolved executions
- operator recovery action capture
- recovery rationale capture
- provider reference attachment
- manual recovery history
- state transitions to manually resolved, cancelled, or reopened
- centralized audit trail
- audit events for policy evaluation, approval, execution request creation, provider attempts, reconciliation, and manual recovery
- chronological case-level audit history
- structured JSON audit event details

Policy evaluation must happen before approval. Approval must happen before execution request creation. Execution requests will later be used by provider execution, retry, and reconciliation workflows.


## Target Users

| User               | Responsibility                                                            |
| ------------------ | ------------------------------------------------------------------------- |
| Billing Ops Agent  | Reviews billing correction cases and prepares them for approval           |
| Finance Manager    | Approves or rejects money-impacting corrections                           |
| Execution Operator | Monitors failed executions, retries, and recovery paths                   |
| RevOps Lead        | Tracks operational health, execution reliability, and reconciliation gaps |

## Intended Workflow

Billing issue
→ human review
→ approval
→ execution request
→ external provider write
→ success / failure / timeout
→ retry / reconciliation
→ manual recovery if needed
→ audit trail

## Architecture Direction

Streamlit UI
→ Case Service
→ Policy + Approval Services
→ Execution Service
→ Billing Provider Adapter
→ Reconciliation Service
→ SQLite Persistence + Audit Trail

## AI and Deterministic System Boundary

This project will maintain a clear boundary between AI assistance and deterministic system control.

| Area                  | Role                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| AI assistance         | Summarize billing issue, identify missing evidence, draft customer-facing context                                   |
| Deterministic systems | Policy evaluation, approval rules, execution state transitions, idempotency, retries, reconciliation, audit logging |

The product principle is:

> AI prepares context. Humans approve. Deterministic systems execute. Reconciliation proves completion.

## Current Seed Case Examples

The project currently includes synthetic billing cases such as:

* duplicate charge
* wrong plan price
* missing contract discount
* goodwill credit request
* possible duplicate correction
* currency mismatch

These cases are designed to support future policy, approval, execution, and reconciliation scenarios.

## How to Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m streamlit run app.py
```

## Current Limitations

The current version does not yet include:

- real Stripe test-mode execution
- background scheduled retries
- provider webhooks
- production-grade permissions
- production observability

These are planned for upcoming commits.

## Future Improvements

Planned future improvements include:

* approval workflow with approver rationale
* deterministic policy engine
* durable execution request model
* idempotency key generation
* mock billing provider adapter with controlled failure modes
* Stripe test-mode adapter
* retry handling for transient failures
* manual recovery queue
* reconciliation dashboard
* execution attempt audit trail
* operational metrics dashboard
