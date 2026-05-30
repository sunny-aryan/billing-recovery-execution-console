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
