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

## Commit 7 Product Decision: Retry Only Transient Failures

Commit 7 adds retry handling for transient execution failures.

This is important because execution failures should not all be treated the same:

- transient failures may be retried
- permanent failures should not be retried automatically
- unknown provider states should move toward reconciliation or manual review
- successful executions should never be retried

The workflow now separates:

- first provider attempt
- transient failure classification
- retry eligibility
- retry attempt
- max retry handling

## Commit 7 Workflow Progression

The product now supports:

billing case  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ mock provider execution attempt  
→ transient failure  
→ retry attempt  
→ succeeded / failed_transient / failed_permanent / needs_manual_review

The key product boundary is:

> Retry is governed by deterministic policy. It is not a generic repeat button.

## Commit 8 Product Decision: Reconciliation Before Manual Recovery

Commit 8 adds reconciliation against a mock provider source of truth.

This is important because manual recovery should be based on verified state, not only on internal status.

The workflow now separates:

- execution attempt result
- internal execution state
- provider source-of-truth lookup
- reconciliation result
- routing to reconciled or manual review

## Commit 8 Workflow Progression

The product now supports:

billing case  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ mock provider execution attempt  
→ retry if transient  
→ reconciliation against provider source of truth  
→ reconciled / needs manual review

The key product boundary is:

> Internal status is not enough. Reliable execution requires source-of-truth verification.

## Commit 9 Product Decision: Manual Recovery as a Governed Workflow

Commit 9 adds manual recovery for unresolved execution states.

This is important because some execution failures cannot be safely retried or automatically reconciled. In those cases, the system needs a controlled operator path.

Manual recovery captures:

- operator name
- recovery action
- rationale
- optional provider reference
- previous execution status
- new execution status

## Commit 9 Workflow Progression

The product now supports:

billing case  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ mock provider execution attempt  
→ retry if transient  
→ reconciliation against provider source of truth  
→ manual recovery if unresolved  
→ manually resolved / cancelled / reopened

The key product boundary is:

> Human intervention is allowed, but it must be explicit, reasoned, and recorded.

## Commit 10 Product Decision: Audit as a Cross-Cutting System Layer

Commit 10 adds centralized audit logging across the execution workflow.

This is important because reliable execution is not only about completing actions safely. It is also about making every important action explainable after the fact.

The audit trail captures:

- policy evaluation
- approval decisions
- execution request creation
- provider execution attempts
- retries
- reconciliation results
- manual recovery actions

## Commit 10 Workflow Progression

The product now supports:

billing case  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ provider execution attempt  
→ retry if transient  
→ reconciliation  
→ manual recovery if unresolved  
→ centralized audit trail

The key product boundary is:

> Workflow tables store current and historical state. Audit events explain the lifecycle across systems and actors.

## Commit 11 Product Decision: Operational Visibility After Auditability

Commit 11 adds an execution operations dashboard.

This is important because the product should not only support individual case workflows. Operators also need a cross-case view of execution health and recovery burden.

The dashboard summarizes:

- execution status distribution
- case status distribution
- provider attempt outcomes
- reconciliation runs
- mismatch or unknown-state count
- manual recovery actions
- executions needing attention
- unreconciled executions

## Commit 11 Workflow Progression

The product now supports both:

case-level workflow:  
billing case → policy → approval → execution → retry → reconciliation → manual recovery → audit

and portfolio-level operations:  
execution health → needs-attention queue → unreconciled queue → recovery workload

The key product boundary is:

> Case workflows help individual operators act. Operations dashboards help teams manage execution reliability at scale.

## Commit 12 Product Decision: Test Execution Reliability Before External Integration

Commit 12 adds automated tests for the deterministic execution workflow.

This is important because the system now includes multiple control layers:

- policy evaluation
- approval gating
- execution request creation
- idempotency
- provider attempt tracking
- retry handling
- reconciliation
- manual recovery
- audit logging

Before adding a real external provider, the internal execution model should be tested.

## Commit 12 Workflow Progression

The product now supports both:

execution workflow:  
policy → approval → execution request → provider attempt → retry → reconciliation → manual recovery → audit

and validation workflow:  
deterministic rules → isolated test database → automated test coverage → safer future provider integration

The key product boundary is:

> External APIs add realism, but tests protect the execution model.

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


## Commit 13 Product Decision: Demo-Safe External Dependency Modes

Commit 13 adds external dependency mode controls for OpenAI and Stripe before either live integration is implemented.

This is important because the product needs to support two modes of operation:

- real external API behavior for realism
- forced mock behavior for stable demos and offline review

OpenAI and Stripe are controlled independently because one dependency can fail or be mocked while the other remains live.

The key product distinction is:

> Forced mock is a deliberate demo choice. Fallback is a runtime recovery path after a live dependency fails.

## Commit 13 Workflow Progression

The product now prepares for external realism without making the workflow brittle.

Upcoming commits will use these controls for:

- OpenAI billing case brief generation
- Stripe test payment setup
- Stripe refund execution
- Stripe refund reconciliation

## Commit 14 Product Decision: AI Brief as Advisory Context

Commit 14 adds an OpenAI-powered billing case brief with forced mock and fallback behavior.

This improves reviewer workflow without weakening execution controls.

The AI brief helps with:

- summarizing billing issue context
- identifying missing evidence
- highlighting risk notes
- drafting customer-facing language

It does not:

- approve billing corrections
- determine policy eligibility
- create execution requests
- call providers
- retry failures
- reconcile provider state
- manually recover cases

## Commit 14 Workflow Progression

The product now supports:

billing case  
→ AI case brief  
→ deterministic policy evaluation  
→ human approval  
→ durable execution request  
→ provider execution  
→ retry / reconciliation / recovery / audit

The key product boundary is:

> AI helps reviewers understand the case, but it does not control the money-impacting workflow.

## Commit 15 Product Decision: Stripe Behind a Provider Boundary

Commit 15 adds the Stripe provider adapter foundation.

This is intentionally done before Stripe test payment setup or refund execution.

The product now distinguishes:

- internal execution lifecycle
- provider adapter boundary
- mock provider for deterministic failure scenarios
- Stripe test-mode provider for real external API realism

This prepares the project to add real Stripe refund execution without weakening the internal reliability model.

The key product boundary is:

> Execution services own workflow state. Provider adapters own external API behavior.

## Commit 16 Product Decision: Stripe Test Payment Before Refund Execution

Commit 16 adds Stripe test payment setup.

This prepares the product for real Stripe refund execution while keeping the workflow controlled.

The system now supports:

- live Stripe test-mode PaymentIntent creation
- forced mock payment setup for demos
- fallback metadata when Stripe setup fails
- local persistence of PaymentIntent and Charge metadata

This makes the next execution step possible:

Stripe test payment  
→ approved execution request  
→ Stripe refund execution  
→ Stripe refund reconciliation

The key product boundary is:

> Preparing a refundable provider object is not the same as executing the refund.


## Commit 17 Product Decision: Real Refund Execution After Durable Request

Commit 17 adds Stripe test-mode refund execution.

This is the first real external provider write in the project.

The refund is executed only after:

- deterministic policy evaluation
- human approval
- Stripe test payment setup
- durable execution request creation
- idempotency key generation

This protects the execution boundary and keeps provider writes auditable.

The key product boundary is:

> Stripe performs the external refund, but the internal execution service governs when and how the refund is attempted.

## Commit 18 Product Decision: Stripe Refund Reconciliation

Commit 18 adds Stripe refund reconciliation.

This completes the real external API loop:

Stripe test payment  
→ Stripe refund execution  
→ Stripe refund ID stored  
→ Stripe refund retrieved  
→ internal state reconciled

The system supports:

- live Stripe refund lookup
- forced mock refund lookup
- safe fallback when Stripe lookup fails
- routing unknown provider state to manual review

The key product boundary is:

> The provider write creates the external object. Reconciliation verifies that the provider object still matches internal state.

## Commit 19 Product Decision: Make Reliability State Legible

Commit 19 improves workflow UX and dependency visibility.

This is important because a reliable execution system has many states and control points. Operators need to understand:

- where the case is in the lifecycle
- what action is allowed next
- whether OpenAI or Stripe are live or mocked
- whether an external dependency result came from live behavior, forced mock, or fallback
- which provider object and idempotency key are attached to the execution

The key product boundary is:

> Backend reliability is not enough. Operators need legible workflow state to act safely.

