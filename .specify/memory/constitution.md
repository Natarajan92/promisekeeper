# PromiseKeeper Constitution

## Core Principles

### I. Specification Before Implementation

Every implementation increment MUST have written requirements and observable acceptance
criteria before application code is written. Its specification MUST identify the user
outcome, scope, evidence inputs, expected behavior, failure behavior, and relevant safety
constraints. Plans and tasks MUST trace to those requirements. Changed behavior MUST be
reflected in the specification before implementation proceeds.

### II. Small, Independently Testable Increments

Work MUST be divided into bounded increments with explicit inputs, outcomes, and
verification steps. Each increment MUST be independently testable, using fictional
fixtures or contract substitutes when dependencies are unavailable. No task or
implementation phase MAY encompass the entire application. Unrelated capabilities MUST
be separate tasks so progress and failures remain reviewable.

### III. Separation of Responsibilities

Domain logic, tools, agents, orchestration, persistence, and presentation MUST have
explicit boundaries. Domain rules MUST be testable without an LLM, user interface,
external tool, or database. Tools MUST expose bounded capabilities; agents MUST reason
through those contracts; orchestration MUST own execution flow and recovery;
persistence MUST own durable storage; presentation MUST expose case information and
human controls. Components MUST NOT bypass these boundaries to create hidden side effects.

### IV. Bounded Agent Architecture

The system MUST start with exactly one LLM-driven agent. The maximum specialized agent
roles are Investigator, Strategist, and Communicator; additional named roles, hidden
subagents, or duplicate autonomous instances used to evade this limit MUST NOT be added.
Investigator covers evidence gathering and reconciliation, Strategist covers responsible
next-action recommendations, and Communicator covers communication drafting. The initial
agent's responsibilities and tools MUST be explicitly scoped. Remaining work MUST be
deterministic, human-operated, or deferred.
Adding a second or third role MUST require a documented need, typed handoffs, acceptance
criteria, and human authorization for the relevant implementation phase.

### V. Deterministic Financial and Safety Logic

Financial calculations, date comparisons, validation, and safety invariants MUST execute
in deterministic code. Monetary representation, currency handling, rounding, timezone,
and date-boundary rules MUST be explicit in the relevant specification and tested.
LLMs MAY extract candidate values or propose interpretations, but their output MUST be
validated before use and MUST NOT determine authoritative balances, overdue status,
approval eligibility, or permission to perform side effects.

### VI. Typed Boundary Contracts

Tool inputs and outputs, agent handoffs, and API requests and responses MUST use explicit,
versioned or compatibly evolved typed contracts. Contracts MUST describe required and
optional fields, evidence references, and error outcomes. Untrusted external data and
LLM output MUST undergo runtime validation at entry boundaries; static types alone are
insufficient. Invalid payloads MUST fail safely without initiating side effects.

### VII. Traceable Evidence and Explicit Uncertainty

Every recommendation MUST reference supporting records through stable identifiers and
retain source provenance. Cases MUST distinguish customer claims, payment commitments,
inferred interpretations, and verified transactions. A promise, message, or unverified
payment assertion MUST NOT be treated as proof of settlement. Missing or contradictory
records MUST remain visible, with the unresolved question and its effect on the
recommendation stated. If evidence is insufficient, the responsible next action MUST
seek clarification or human review instead of asserting an unsupported conclusion.

### VIII. Human Control of Consequential Writes

Consequential write actions MUST require explicit human approval bound to the reviewed
action, target, and final payload. Changes to that payload MUST invalidate prior approval.
At minimum, customer communication, writes to external business records, and changes to
authoritative financial or commitment records are consequential. Approval and execution
MUST be auditable. Every customer message MUST be reviewed and individually initiated by
a human; unattended, scheduled, agent-triggered, or blanket-preapproved sending MUST NOT
occur. Routine internal case-state persistence MAY proceed without approval only when
it neither authorizes external effects nor promotes an unverified claim to a verified fact.

### IX. Durable State and Safe Recovery

Case state, evidence references, decisions, approvals, action attempts, and outcomes
needed for recovery MUST be persisted. Retries MUST have explicit limits and exhaustion
behavior. Side-effecting operations MUST use idempotency or equivalent duplicate
prevention that survives retries, restarts, and repeated human submissions. Failures
MUST leave a recoverable, inspectable state. If an external write has an unknown outcome,
the system MUST reconcile or request human review before attempting it again.

### X. Tests for Normal, Uncertain, and Failed Outcomes

Each implemented increment MUST include tests tied to its acceptance criteria. The
relevant test set MUST cover happy paths, missing information, contradictory records,
and failure recovery, including retry exhaustion and duplicate prevention for side
effects. Financial, date, validation, and approval invariants MUST have deterministic
tests. LLM-dependent behavior MUST have defined evaluation cases and review criteria;
a plausible demonstration alone MUST NOT establish correctness. Tests MUST accompany
development instead of being deferred until the whole application is built.

### XI. Recorded Architectural Decisions

Important architectural decisions and tradeoffs MUST be recorded in an architecture
decision record before, or with, the increment that depends on them. Each record MUST
state context, the decision, alternatives considered, consequences, and relevant
constraints. Decisions involving agent count, layer boundaries, financial truth,
approvals, persistence, recovery, or MVP scope MUST be documented. Superseded decisions
MUST remain traceable.

### XII. Case-Centric User Experience

The primary unit of work MUST be a payment follow-up case. The interface MUST make the
case's commitments, available evidence, transaction verification status, unresolved
questions, current state, recommended next action, and communication review accessible.
Conversation MAY assist a case, but chat history MUST NOT be the sole source of case
state or the only way to inspect evidence, review a draft, or approve an action.

### XIII. Fictional Test Data and Information Protection

Tests, demonstrations, fixtures, and evaluation datasets MUST use fictional customer and
business data. Secrets MUST NOT be committed or exposed in prompts, logs, screenshots,
fixtures, or user-visible errors. Customer information MUST be access-controlled and
limited to what the authorized case workflow requires. Tool and model inputs MUST
minimize sensitive data; persisted artifacts and logs MUST apply appropriate redaction.
The implementation specification MUST define access, retention, and deletion rules
before handling real customer information.

### XIV. Fixed MVP Deadline and Scope Discipline

The MVP deadline is 2026-10-26 10 AM IST and MUST be treated as a strict scope constraint.
Every proposed increment MUST be identified as essential to the approved MVP acceptance
criteria or deferred beyond the MVP. When available time and scope conflict, scope MUST
be reduced; evidence integrity, human approval, safety invariants, tests, and truthful
reporting MUST NOT be waived to meet the date. The deadline MUST NOT authorize a larger
task, an unapproved phase transition, or automatic expansion to three agents.

### XV. Human Review Between Implementation Phases

Implementation phases MUST have named scope, exit criteria, and a designated human
reviewer before implementation begins. At each phase boundary, work MUST stop and present
the completed changes, acceptance evidence, tests actually executed, unresolved issues,
and proposed next phase. The next phase MUST NOT begin until a human explicitly
authorizes it. Silence, a prior broad project request, passing checks, or deadline
pressure MUST NOT count as authorization.

### XVI. Truthful Verification Reports

Reports MUST identify only tests and evaluations actually executed and accurately state
their outcomes. Planned, skipped, blocked, failed, and unexecuted checks MUST be labeled
as such. Reports MUST NOT invent pass counts, coverage, evaluation scores, recovery
results, or production readiness. Claims of completion MUST be supported by the relevant
acceptance evidence and recorded verification commands or evaluation procedures.

## Product Boundaries and Open Decisions

PromiseKeeper is an evidence-first, agentic payment follow-up assistant for small B2B
service businesses. It helps owners understand customer payment commitments, reconcile
available evidence, decide the responsible next action, and review follow-up communication.
It MUST preserve the distinction between advice, a customer assertion, and a verified
transaction throughout the case lifecycle.

The following decisions remain open. They do not weaken the principles above and MUST
be resolved in the relevant specification or approved phase plan before dependent
implementation begins:

- TODO(INITIAL_AGENT_ROLE): Define the first LLM-driven agent's responsibilities within
  the three allowed roles, its tools, and its deterministic or human-operated support.
- TODO(EVIDENCE_VERIFICATION): Define acceptable transaction sources, verification and
  reconciliation rules, source precedence, and treatment of conflicting records.
- TODO(APPROVAL_BOUNDARIES): Enumerate consequential actions beyond the minimum in
  Principle VIII; define approver authority, approval validity, and whether individual
  human-initiated sends occur in PromiseKeeper or in an external communication tool.
  Automatic customer sending remains prohibited in either design.
- TODO(PHASE_GATES): Name the implementation phases, their reviewers, acceptance evidence,
  and exit criteria. No phase may cover the entire application.
- TODO(MVP_RELEASE): Define the minimum release acceptance criteria, deadline cutoff time,
  and governing timezone for 2026-10-25. No extension of the deadline may be inferred.

## Development Workflow and Review Gates

1. Specify the case outcome, requirements, acceptance criteria, exclusions, and applicable
   open decisions before planning implementation.
2. Produce a plan that identifies layer boundaries, typed contracts, deterministic
   invariants, evidence flow, approval controls, persistence, and failure recovery.
   Record material architectural decisions and identify MVP-essential scope.
3. Split the plan into small, independently testable tasks within named implementation
   phases. Obtain human authorization before starting the first implementation phase.
4. Implement and verify only the authorized phase. Maintain requirement-to-task and
   requirement-to-test traceability. Changes in scope MUST update the specification
   and plan before the affected work proceeds.
5. At each phase boundary, deliver a reviewable result and an accurate verification
   report, then stop. Continue only after explicit human authorization for the next phase.
6. Before MVP acceptance, verify the agreed release criteria and disclose all unresolved
   failures, unexecuted checks, and deferred scope. Deadline pressure MUST NOT bypass
   any required review or safety gate.

## Governance

This constitution is the authoritative engineering policy for PromiseKeeper.
Specifications, plans, tasks, code reviews, and phase reviews MUST demonstrate compliance.
Conflicting artifacts MUST be corrected before the affected implementation continues.

Amendments MUST state the proposed change, rationale, affected principles and artifacts,
and any required migration or revalidation. A project-owner-designated human MUST approve
amendments before they take effect. No implementation task, architecture decision, or
deadline exception may silently override a principle.

Constitution versions MUST follow semantic versioning: MAJOR for incompatible principle
removals or redefinitions; MINOR for new principles, sections, or materially expanded
obligations; PATCH for clarifications without changed obligations. Every amendment MUST
update the last-amended date and preserve the original ratification date.

Each implementation plan and phase review MUST include a constitution compliance check.
A violation MUST be corrected or addressed by an approved constitutional amendment before
the affected work proceeds. Open decisions MUST be resolved explicitly and MUST NOT be
treated as permission to weaken an invariant.

Version 1.0.0 establishes the initial constitution on 2026-10-23. Subsequent governance
changes MUST follow the amendment procedure above.

**Version**: 1.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
