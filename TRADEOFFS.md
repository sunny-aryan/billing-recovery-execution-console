# Trade-offs

## Commit 1 and 2: Start with workflow foundation before external API integration


### Decision

The first implementation focuses on the billing case queue, case detail view, seed data, SQLite persistence, and project documentation before adding Stripe or any external billing provider.

### Why

The main portfolio signal is not the API call itself.

The signal is the reliable execution system around the API call:

* human approval
* durable execution request
* idempotency
* retries
* reconciliation
* auditability
* manual recovery

Starting with the workflow foundation keeps the product model clear before introducing provider complexity.

### Alternative Considered

Start directly with Stripe test-mode integration.

### Why Rejected for Now

That would risk making the project look like a Stripe API demo instead of an operations execution system.

The project should first make the workflow and execution lifecycle clear, then add the external provider adapter.

### Future Direction

Add a provider adapter layer with both:

* real Stripe test-mode execution
* mock provider failure modes for deterministic demos

The mock provider is important because it allows the product to reliably demonstrate:

* provider success
* transient failure
* permanent failure
* timeout
* provider success with internal state uncertainty
* reconciliation mismatch


## Commit 3: Add deterministic policy evaluation before approval

### Decision

The project adds deterministic policy evaluation before human approval or execution workflows.

### Why

Billing corrections are money-impacting actions. Before a human can approve a correction, the system should determine whether the case is eligible, blocked, or requires manager approval using deterministic rules.

This creates a control layer that future approval and execution workflows can depend on.

### Alternative Considered

Allow cases to move directly from review to human approval.

### Why Rejected

That would make approval too dependent on human judgment alone and would weaken the product’s core safety model.

For this project, approval should not be the first control. Policy evaluation should happen before approval, and execution should happen only after approval.

### Product Principle Reinforced

AI can assist with context, but deterministic systems must govern money-impacting workflow eligibility.

## Commit 4: Persist human approval before execution

### Decision

The project adds a persisted human approval workflow before introducing execution requests or provider writes.

### Why

Reliable execution should not begin from a UI button alone. It should begin from a durable human decision that records:

- who approved
- what role they had
- what policy evaluation was used
- what action was approved
- what amount was approved
- why the decision was made

This creates a clear control point before future money-impacting execution.

### Alternative Considered

Move directly from policy evaluation to execution request creation.

### Why Rejected

That would weaken the product’s governance model.

For this project, execution must be downstream of both deterministic policy evaluation and explicit human approval.

### Product Principle Reinforced

Do not execute what has not been approved.  
Do not approve what policy has not evaluated.

## Commit 5: Create execution requests before provider execution

### Decision

The project adds durable execution request creation before adding provider API calls.

### Why

A human approval should not directly trigger an external provider write.

The system should first create a durable internal execution request that records:

- the source case
- the approval used
- the operation type
- the amount
- the provider target
- the execution status
- the idempotency key

This creates a reliable internal command that future provider execution attempts can use.

### Alternative Considered

Call the provider immediately after human approval.

### Why Rejected

That would blur approval, execution request creation, and provider execution into one step.

Real execution systems need durable intermediate state so failures can be retried, audited, and reconciled.

### Product Principle Reinforced

Human approval authorizes execution.  
Execution requests make that authorization durable.  
Provider attempts should be separate, retryable, and auditable.

## Commit 6: Use a mock provider before real Stripe execution

### Decision

The project adds mock provider execution before adding Stripe test-mode execution.

### Why

The goal of this stage is to model execution behavior, state transitions, and attempt tracking without being blocked by external provider setup.

A mock provider also allows deterministic demonstration of failure modes that are hard to force reliably with real APIs:

- success
- transient failure
- permanent failure
- timeout
- unknown provider state

### Alternative Considered

Integrate Stripe immediately.

### Why Rejected

Starting with Stripe would make the project look like an API integration demo and would make controlled failure testing harder.

The stronger product signal is to first model provider execution as an adapter boundary, then add a real provider behind that boundary later.

### Product Principle Reinforced

Provider execution should be isolated behind an adapter.  
The internal execution lifecycle should not depend on one provider’s API shape.

## Commit 7: Manual retry before background retry automation

### Decision

The project adds manual retry handling for transient execution failures before introducing automated background retries.

### Why

The portfolio goal at this stage is to demonstrate retry eligibility, retry-safe state transitions, attempt tracking, and retry limits.

A manual retry button keeps the workflow easy to inspect and demo while still modeling the important execution reliability concepts.

### Alternative Considered

Add scheduled background retries immediately.

### Why Rejected

Background retries would require workers, scheduling, backoff timing, and async execution concerns that could distract from the core product concept.

For this stage, the important distinction is not whether retry is scheduled or manual. The important distinction is that only transient failures are retryable, retries reuse the same execution request and idempotency key, and retry attempts are recorded.

### Product Principle Reinforced

Retry is not just “try again.”  
Retry is a governed recovery action with eligibility rules, attempt limits, and auditability.

## Commit 8: Add reconciliation before manual recovery

### Decision

The project adds reconciliation before building a full manual recovery workflow.

### Why

Manual recovery should be driven by a known mismatch or unknown provider state, not by vague failure status.

Reconciliation creates the verification layer that determines whether internal execution state matches the provider source of truth.

### Alternative Considered

Move directly from failed or unknown execution states into manual recovery.

### Why Rejected

That would skip the verification step.

In real execution systems, operators need to know whether the provider actually performed the action before deciding whether to retry, manually resolve, or escalate.

### Product Principle Reinforced

Execution is not complete when the provider call returns.  
Execution is complete when internal state and provider source of truth are reconciled.

## Commit 9: Manual recovery after reconciliation

### Decision

The project adds manual recovery after reconciliation, rather than immediately after provider failure.

### Why

Manual recovery should be based on a clear understanding of the execution state.

By placing reconciliation before manual recovery, the system can distinguish between:

- confirmed provider success
- confirmed provider non-execution
- unknown provider state
- internal/provider mismatch

Operators can then record a recovery action with rationale.

### Alternative Considered

Allow manual recovery directly after any provider failure.

### Why Rejected

That would make recovery less disciplined.

In a reliable execution system, operators should first understand whether the external provider actually performed the action before deciding how to recover.

### Product Principle Reinforced

Manual recovery is not a shortcut around system controls.  
It is a governed path for cases automation cannot safely resolve.

## Commit 10: Centralized audit trail after core workflow maturity

### Decision

The project adds centralized audit logging after policy, approval, execution, retry, reconciliation, and manual recovery are already modeled.

### Why

Each workflow table stores domain-specific state, but operators and auditors need a chronological event history across the entire case lifecycle.

A centralized audit trail answers:

- what happened
- when it happened
- who or what performed the action
- which entity changed
- what structured details were recorded

### Alternative Considered

Rely only on individual workflow tables such as approvals, execution attempts, and reconciliation runs.

### Why Rejected

Those tables are useful for workflow state, but they do not provide a unified timeline.

A reliable execution system needs both domain tables and a cross-cutting audit log.

### Product Principle Reinforced

Money-impacting workflows must be explainable after the fact.

## Commit 11: Add operations dashboard before real provider integration

### Decision

The project adds an execution operations dashboard before integrating a real external billing provider.

### Why

The current project already models the core execution lifecycle with a realistic mock provider. Before adding provider-specific complexity, the system should expose operational health across cases.

The dashboard helps users answer:

- what needs attention
- what is unreconciled
- how often execution attempts fail
- how often reconciliation finds mismatches
- how often manual recovery is needed

### Alternative Considered

Move directly to Stripe test-mode integration.

### Why Rejected for Now

A real provider integration would improve external realism, but it would not automatically improve operational visibility.

For a Senior/Principal PM portfolio signal, it is important to show that execution reliability is not only about making API calls. It is also about monitoring outcomes, prioritizing recovery work, and understanding reliability trends.

### Product Principle Reinforced

Reliable execution requires both workflow controls and operational visibility.

## Commit 12: Add tests before real provider integration

### Decision

The project adds automated tests before introducing a real Stripe test-mode adapter.

### Why

The system now contains important deterministic reliability logic:

- policy eligibility
- approval gating
- idempotency
- execution state transitions
- retry eligibility
- reconciliation outcomes
- manual recovery validation

Before adding real provider complexity, these rules should be protected by automated tests.

### Alternative Considered

Move directly to Stripe integration.

### Why Rejected for Now

A real provider adapter would increase external realism, but it would also introduce setup complexity and failure modes unrelated to the internal execution model.

Testing first makes the internal execution system more trustworthy before adding real API writes.

### Product Principle Reinforced

Reliable execution systems need reliable controls.  
Reliable controls should be tested before they are connected to real external providers.

## Commit 13: External dependency modes before external API integration

### Decision

The project adds dependency mode controls before implementing OpenAI or Stripe calls.

Each external dependency can be independently configured as:

- live external API
- forced mock / demo mode

### Why

The project should be demo-friendly and resilient. Reviewers should be able to run the workflow without needing external API calls in every demo situation.

This also separates two important concepts:

- forced mock behavior, which is a deliberate user-selected demo mode
- fallback behavior, which happens when a live dependency call fails

### Alternative Considered

Add OpenAI and Stripe calls directly without mode controls.

### Why Rejected

That would make the app brittle during demos and would hide an important product concern: external dependencies are not always available or desirable to call.

### Product Principle Reinforced

External integrations should improve realism without making the core workflow fragile.

## Commit 14: Advisory AI before deterministic policy

### Decision

The project adds an AI-generated billing case brief before deterministic policy evaluation.

### Why

Reviewers benefit from a concise summary of the billing issue, customer impact, missing evidence, and risk notes before deciding whether to proceed with policy evaluation and approval.

The AI brief is intentionally advisory. It does not change policy outcomes, approval decisions, execution states, reconciliation results, or manual recovery actions.

### Alternative Considered

Let AI recommend approval or execution actions.

### Why Rejected

That would blur the project’s core control model.

For money-impacting workflows, AI can prepare context, but deterministic systems and humans must govern approval and execution.

### Product Principle Reinforced

AI prepares context.  
Policy determines eligibility.  
Humans approve.  
Deterministic systems execute.

## Commit 15: Stripe provider adapter foundation before payment execution

### Decision

The project adds a Stripe provider adapter foundation before creating test payments or refunds.

### Why

A reliable execution system should not couple the execution service directly to one external provider SDK.

This commit establishes Stripe as a provider behind an adapter boundary while keeping mock provider behavior available for deterministic failure-mode demos.

### Alternative Considered

Add Stripe refund execution directly inside the execution service.

### Why Rejected

That would blur internal execution logic with provider-specific API details.

The execution service should manage lifecycle state, idempotency, attempts, retries, reconciliation, and audit. Provider adapters should handle provider-specific calls.

### Product Principle Reinforced

External provider realism should be added behind stable internal execution boundaries.

## Commit 16: Separate Stripe test payment setup from refund execution

### Decision

The project adds Stripe test payment setup before Stripe refund execution.

### Why

A refund requires an existing payment object. Separating test payment setup from refund execution keeps the workflow easier to understand and debug.

This also lets the project demonstrate external provider preparation without immediately coupling it to refund execution.

### Alternative Considered

Create a Stripe test payment and refund it in the same workflow step.

### Why Rejected

That would blur two different operational events:

- preparing an external payment source
- executing a refund against that source

Keeping them separate makes the execution lifecycle clearer.

### Product Principle Reinforced

External execution should be decomposed into durable, inspectable steps.

## Commit 17: Stripe refund execution behind execution request boundary

### Decision

The project adds Stripe test-mode refund execution only after policy evaluation, human approval, Stripe test payment setup, and durable execution request creation.

### Why

A real external refund write should not happen directly from an approval action.

It should happen through a durable execution request that contains the approved amount, operation type, provider target, and idempotency key.

### Alternative Considered

Call Stripe refund immediately after approval.

### Why Rejected

That would collapse approval and execution into one step and would weaken retry, audit, and reconciliation behavior.

### Product Principle Reinforced

Human approval authorizes the correction.  
The execution request makes it durable.  
The provider adapter performs the external write.

## Commit 18: Stripe reconciliation after Stripe refund execution

### Decision

The project adds Stripe refund reconciliation after Stripe refund execution.

### Why

A refund is not complete simply because the internal system marked the execution as succeeded.

The system should verify that the external provider still agrees with the internal state by retrieving the Stripe refund status.

### Alternative Considered

Trust the original Stripe refund creation response permanently.

### Why Rejected

Provider state can be incomplete, delayed, or misunderstood by internal systems.

A reliable execution workflow should have a verification step that compares internal state against provider source of truth.

### Product Principle Reinforced

External execution is complete only after provider state is verified.

## Commit 19: Polish workflow visibility before screenshots

### Decision

The project improves workflow UX and dependency status visibility before adding final screenshots and documentation polish.

### Why

The system now has many important workflow layers: AI brief, policy, approval, Stripe test payment setup, execution request, provider execution, retry, reconciliation, manual recovery, audit, and dashboard.

Without clearer workflow summary and dependency state visibility, the product could feel technically strong but hard to evaluate quickly.

### Alternative Considered

Move directly to screenshots and final README polish.

### Why Rejected

Screenshots should capture the polished workflow, not the rough version.

This commit makes the system easier to understand before final portfolio packaging.

### Product Principle Reinforced

Operational systems need clear next-action guidance, not just correct backend state.
