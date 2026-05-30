# Trade-offs

## Commit 1/2: Start with workflow foundation before external API integration

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
