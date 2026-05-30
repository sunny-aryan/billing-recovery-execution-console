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
