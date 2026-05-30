# Product Notes

## Portfolio Goal

Project 4 is designed to show progression from recommendation and approval workflows into reliable execution and recovery.

Previous portfolio projects demonstrated:

* decision support
* human-in-the-loop workflows
* product-grade operations UX
* external dependency awareness

This project focuses on what happens after approval:

* durable execution requests
* external writes
* idempotency
* retry logic
* reconciliation
* manual recovery
* auditability

## Product Principle

AI can help prepare context, but deterministic systems must govern money-impacting execution.

## Project 4 Progression

Portfolio progression so far:

Project 1: decision-support system
→ Project 2: operational workflow system
→ Project 3: product-grade workflow experience
→ Project 4: reliable execution and recovery system

The intended Project 4 signal is:

> This system does not stop at recommending or approving an action. It models how approved actions are safely executed, monitored, retried, reconciled, and recovered.

## Commit 1/2 Scope

The first implementation establishes the basic billing recovery workspace:

* billing correction queue
* case detail view
* persisted synthetic cases
* modular architecture for future execution workflow

## Commit 3 Product Decision: Policy Before Approval

Policy evaluation was added before human approval because money-impacting corrections should not move directly from case review to approval.

This creates a deterministic control layer that future approval and execution workflows will depend on.

The lifecycle now begins to separate:

- case review
- policy evaluation
- approval eligibility
- future execution readiness

## Commit 3 Workflow Progression

The product now supports:

```text
billing case
→ deterministic policy evaluation
→ eligible / manager approval required / needs review / blocked
→ future approval workflow
→ future execution workflow
```

## Commit 4 Product Decision: Approval as a Durable Workflow Object

Commit 4 adds persisted human approval decisions.

This is important because approval is not just a UI interaction. For a money-impacting workflow, approval needs to be a durable object that captures:

- approver identity
- approver role
- decision
- approved action
- approved amount
- rationale
- policy evaluation used at decision time

This prepares the system for execution requests in the next commit.

## Commit 4 Workflow Progression

The product now supports:

```text
billing case
→ deterministic policy evaluation
→ human approval or rejection
→ future execution request
```

## Commit 5 Product Decision: Execution Request Before Provider Write

Commit 5 adds durable execution request creation with deterministic idempotency keys.

This is important because the system should not call an external billing provider directly from the approval action.

The workflow now separates:

- human approval
- execution request creation
- future provider execution attempt
- future reconciliation

This separation makes the execution lifecycle easier to reason about, retry, audit, and recover.

## Commit 5 Workflow Progression

The product now supports:

```text
billing case
→ deterministic policy evaluation
→ human approval
→ durable execution request
→ future provider execution
```

The key product boundary is: 

> Approval authorizes the correction. The execution request turns that authorization into a durable system command. Provider execution remains a separate step.

## Commit 6 Product Decision: Attempt Tracking Before Retry

Commit 6 adds mock provider execution and execution attempt tracking.

This is intentionally added before retry logic because the system first needs a durable record of each provider call attempt.

The workflow now separates:

- execution request
- execution attempt
- provider response
- execution status update

This prepares the system for retry and reconciliation in later commits.

## Commit 6 Workflow Progression

The product now supports:

billing case  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ mock provider execution attempt  
→ succeeded / failed_transient / failed_permanent / needs_manual_review

The key product boundary is:

> Execution requests define what should happen. Execution attempts record what actually happened when the provider was called.

## Why Billing Recovery?

Billing corrections are a strong domain for this project because they involve:

* real customer impact
* financial risk
* duplicate execution risk
* external provider dependency
* auditability needs
* manual recovery when automation is unsafe

This makes the domain well-suited for demonstrating reliable execution after human approval.

## Open Product Questions

* Should the first real external write be a Stripe refund or Stripe credit note?
* Should retries be manual-triggered in the MVP or simulated as scheduled retries?
* Which failure mode should be most prominent in the demo?
* How much accounting or revenue context is needed without expanding scope too far?
* Should reconciliation repair internal state automatically or require manual confirmation for certain mismatches?

## Non-goals

This project is not intended to become:

* a full subscription billing system
* a revenue recognition system
* a general accounting platform
* a complete Stripe clone
* a production-grade finance operations tool

The focus is narrower:

> reliable execution lifecycle after human-approved billing correction.


