# Automotive Repair Assurance Platform — implementation roadmap

Status: active product roadmap
Date: 2026-08-16

## Product outcome

Turn repair specifications into controlled execution with attributable evidence
and a verifiable immutable repair record.

```text
Specification → Execution → Evidence → Verification
Skills → Roles → Gates → Escalation
```

AI is a later support layer and is not required by the core workflow.

## Iteration 0 — transition and safety

- [x] create a dedicated branch from a pushed safe point;
- [x] inventory existing diagnostics models, services, UI, infrastructure, and migrations;
- [x] classify reuse / modify / new / later components;
- [x] preserve existing data and legacy diagnostic workflows;
- [x] document the production migration gap;
- [x] avoid applying new migrations to the current production database.

Evidence:

- `AUTOMOTIVE_REPAIR_ASSURANCE_ARCHITECTURE.md`;
- commit `4b21fee docs: define repair assurance architecture pivot`.

## Iteration 1 — minimal executable domain core

### Specification

- [x] reuse the normalized, organization-scoped `Vehicle`;
- [x] add `RepairProcedure`;
- [x] add immutable published `ProcedureVersion`;
- [x] pin every `RepairCase` to one published version;
- [x] add ordered atomic `Operation`;
- [x] add operation dependencies;
- [x] add technical requirements, tools, expected result, skill, role, and QC metadata;
- [x] add extensible `EvidenceRequirement` types;
- [x] separate `ReferenceMedia` from captured `Evidence`;
- [x] model external YouTube references without downloading media.

### Execution

- [x] add `RepairCase` and technician assignments;
- [x] instantiate `CaseOperation` states from a published version;
- [x] expose only dependency-unlocked operations;
- [x] enforce role and verified skill checks in backend services;
- [x] reject unassigned technicians on the backend;
- [x] block completion when mandatory evidence is missing;
- [x] validate measurement units and allowed ranges;
- [x] block downstream steps while approval is pending;
- [x] support senior approve/rework/reject/escalate decisions;
- [x] store evidence used by a decision;
- [x] store operation keys explicitly authorized by a decision.

### Verification and audit

- [x] verify mandatory operations;
- [x] verify mandatory evidence through execution gates;
- [x] verify mandatory approvals through execution states;
- [x] include QC operations in verification;
- [x] return VERIFIED / FAILED / INCOMPLETE / REQUIRES_REVIEW;
- [x] keep Evidence, ExpertDecision, Verification, RepairAuditEvent, and RepairRecord append-only;
- [x] create an immutable checksummed `RepairRecord` snapshot;
- [x] retain user, operation, status transition, and timestamp audit data.

### Minimum UI

- [x] author procedures with Django admin;
- [x] publish versions only through the validated admin action;
- [x] prevent direct admin case creation that bypasses execution initialization;
- [x] create RepairCase through a protected server-side form;
- [x] show mechanics the current operation and blocked operations;
- [x] submit evidence, complete operations, review gates, and run verification;
- [x] enforce tenant and assignment visibility on the server.

### Demonstration proof

- [x] automated steering-rack-style scenario;
- [x] diagnostic scan evidence;
- [x] dependency unlock;
- [x] 105 Nm measurement evidence;
- [x] junior execution and senior approval;
- [x] QC road-test confirmation;
- [x] final VERIFIED result;
- [x] immutable record and audit trail.

Implementation commits:

- `72d800a feat: add repair assurance domain schema`;
- `b7d2824 feat: implement gated repair execution engine`.

## Iteration 2 — pilot hardening

- [x] prepare and review production DB backup and migration rollout;

### Production rollout and admin usability

- [x] deploy the assurance domain core to production without removing legacy data;
- [x] expose the repair-control section to authorized staff without the previous 403;
- [x] localize registered project admin models, fields, choices, columns, and actions;
- [x] add an admin language selector for RU / EN / NL / FR / DE;
- [x] preserve the current admin path, query string, and fragment when switching language;
- [x] localize the admin site heading and the language-selector label;
- [x] compile all gettext catalogs during the production image build;
- [x] verify zero Cyrillic model/field/choice captions in EN / NL / FR / DE;
- [x] deploy the localized admin image and confirm a healthy production container.

Evidence:

- commits `08b44c3`, `a4ca4d5`, `e3eb0cb`, `bea0a41`, `f61ade5`,
  `2c9fe0f`, `a7258fd`, and `bb8841b`;
- assurance test suite: 8/8 passing;
- runtime localization audit: 0 untranslated Cyrillic domain captions for each non-Russian locale.
- [x] add a curated steering rack demo seed with explicit non-OEM disclaimer;
- [x] improve procedure authoring UX and dependency validation;
- [x] add evidence file size, MIME, malware scanning, and storage policy;
- [x] implement an explicit evidence supersession workflow;
- [x] add an append-only workshop walkthrough UX observation log;
- [x] add case cancellation and controlled exception/skip workflow;
- [x] add notification queue for remote expert review;
- [x] add richer audit screens and export;
- [x] add external Repair Certificate projection;
- [ ] conduct one real workshop walkthrough and record UX failures.

### Current position

- Active phase: **Iteration 2 — pilot hardening**.
- Completed: safe rollout plus production admin access and localization.
- Completed in the current hardening pass: curated non-OEM demo seed,
  procedure authoring validation, fail-closed evidence upload hardening, and
  append-only evidence supersession, plus controlled case cancellation and
  operation exceptions, a durable remote expert-review notification queue, and
  role-restricted audit screens with filtered CSV/JSON export, plus a
  privacy-minimized external Repair Certificate.
- Next planned deliverable: **real workshop walkthrough and UX failure log**.
- Iteration 3 has not started.

## Iteration 3 — competency and procedure library

- [ ] evidence-based competency review;
- [ ] certification validity and vehicle scope;
- [ ] moderated Evidence → ReferenceMedia promotion;
- [ ] procedure revision cloning and comparison;
- [ ] external DMS/GMS adapter interface;
- [ ] procedure import provenance and licensing controls.

## AI support layer — later

- [ ] procedure parsing into a reviewable draft;
- [ ] vehicle-specific adaptation suggestions;
- [ ] evidence quality assistance;
- [ ] anomaly detection and QC prioritization.

AI output must never silently publish specifications, grant competency, bypass a
gate, approve evidence, or rewrite a completed repair record.
