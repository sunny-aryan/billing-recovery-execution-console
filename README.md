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
- execution operations dashboard
- execution status summary
- retry and attempt metrics
- reconciliation summary metrics
- manual recovery summary metrics
- needs-attention queue
- unreconciled execution queue
- automated tests for core execution reliability workflows
- external dependency mode controls for OpenAI and Stripe
- demo-safe forced mock mode for upcoming external API integrations
- separate OpenAI and Stripe dependency modes
- AI billing case brief generation
- OpenAI live mode support
- forced mock AI brief mode
- deterministic fallback when OpenAI is unavailable or invalid
- AI brief audit events

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

## AI Case Brief

The Case Detail page includes an AI Case Brief section before policy evaluation.

The brief can include:

- case summary
- customer impact
- missing evidence
- risk notes
- suggested reviewer questions
- customer message draft

The AI brief is advisory only. It does not approve, reject, execute, retry, reconcile, or override deterministic policy.

The OpenAI dependency can run in two modes:

- **Live external API** — calls OpenAI using `OPENAI_API_KEY`
- **Forced mock / demo mode** — returns a deterministic mock brief without making an external API call

If live OpenAI mode fails, the system uses a deterministic fallback brief and records that fallback was used.

## External Dependency Modes

The app includes dependency mode controls for upcoming OpenAI and Stripe integrations.

Each dependency can be configured independently:

- **Live external API** — use real external API behavior when configured.
- **Forced mock / demo mode** — avoid external API calls and use deterministic mock behavior.

OpenAI and Stripe are intentionally controlled separately. One dependency may use live mode while the other uses forced mock mode.

This distinction matters because user-selected mock behavior is different from runtime fallback behavior:

- **Forced mock** is a deliberate demo choice.
- **Fallback** is used when a live dependency call fails and the system must degrade safely.

## AI and Deterministic System Boundary

This project will maintain a clear boundary between AI assistance and deterministic system control.

| Area                  | Role                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| AI assistance         | Summarize billing issue, identify missing evidence, draft customer-facing context                                   |
| Deterministic systems | Policy evaluation, approval rules, execution state transitions, idempotency, retries, reconciliation, audit logging |

The product principle is:

> AI prepares context. Humans approve. Deterministic systems execute. Reconciliation proves completion.

## Operations Dashboard

The app includes an execution operations dashboard that summarizes system health across cases.

It helps operators answer:

- Which executions need attention?
- Which executions are unreconciled?
- How many provider attempts succeeded or failed?
- How often manual recovery is needed?
- Where execution reliability is breaking down?

This dashboard turns the project from a case-by-case workflow into a small operational control console.

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

## Automated Tests

The project includes automated tests for core execution reliability logic.

Test coverage includes:

- deterministic policy evaluation
- idempotency key generation
- execution request duplicate prevention
- mock provider execution outcomes
- retry eligibility and retry attempts
- reconciliation outcomes and mismatch detection
- manual recovery validation
- centralized audit event creation

Run tests locally:

```bash
pytest
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
