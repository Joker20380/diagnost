# Automotive Repair Assurance Platform — architecture transition

Date: 2026-08-16
Status: implementation baseline for the product pivot

## Product boundary

The new core is an executable repair assurance workflow:

```text
Specification → Execution → Evidence → Verification
Skills → Roles → Gates → Escalation
```

AI is optional and must not be required for execution, authorization, evidence
collection, verification, or the audit record.

## Current repository assessment

### Reuse

- `diagnostics.Vehicle` and `VehicleConfiguration`: existing normalized,
  organization-scoped vehicle identity. Extend gradually; do not create a second
  vehicle table.
- `users.Organization`, `Workshop`, `UserProfile`, and
  `TechnicianProfile`: tenant, branch, user, and initial role context.
- `TechnicianProfile.Role`: usable as an initial coarse authorization input.
  It is not sufficient as a competency model.
- The immutable patterns in `DiagnosticRecord`, `DiagnosticApproval`, and
  their checksum services: design reference for repair records and append-only
  decisions.
- Django, PostgreSQL, server-rendered templates, admin, and the existing Docker
  deployment shape.

### Modify or adapt

- Add an independent `assurance` Django app. New repair workflow code must not
  depend on the DTC parser or diagnostic recommendation engine.
- Add minimal `Skill` and `TechnicianSkill` models only for server-side
  operation authorization.
- Keep organization and workshop on repair cases for tenant/branch scoping.
- Reuse uploaded-file infrastructure for evidence, with immutable metadata and
  protected deletion after case completion.
- Use the existing admin for procedure authoring in the first iteration; build
  a mechanic-focused execution UI separately.

### New core

- `RepairProcedure` and immutable published `ProcedureVersion`.
- Ordered `Operation`, operation dependencies, reference media, and evidence
  requirements.
- `RepairCase` pinned to one procedure version.
- `CaseOperation` as the execution state copied from the selected version.
- Append-only `Evidence`, `ExpertDecision`, and `RepairAuditEvent`.
- Deterministic gates, server-side competency checks, verification, and an
  immutable `RepairRecord` snapshot.

### Secondary / legacy

The following remain available but are not dependencies of the new core:

- `DiagnosticSession`, `DiagnosticCase`, complaint/intake, DTC references,
  Launch PDF parsing, diagnostic analysis gate, suspension inspection, and
  diagnostic reports.
- Website/news/projects/contact functionality in `main`.

They may later become integrations or evidence producers for a repair case.

### Later or remove only after migration evidence

- AI diagnosis as a product center.
- Legacy diagnostic lifecycle as the primary navigation.
- Duplicate recommendation and suspension workflows.
- Website/CMS modules unrelated to the assurance product.

No existing data or feature is removed in this iteration.

## Business invariants

1. A repair case pins a specific published procedure version.
2. A published procedure version and its specification cannot be edited.
3. Only currently available operations may be executed.
4. Authorization is enforced in services, not only in templates.
5. Completion requires every mandatory evidence requirement to be satisfied.
6. A blocking operation prevents dependent operations from becoming available.
7. Approval decisions and evidence are append-only and attributable.
8. Verification is deterministic and returns VERIFIED, FAILED, INCOMPLETE, or
   REQUIRES_REVIEW.
9. A completed case produces an immutable snapshot and audit trail.
10. Reference media and captured evidence are separate entities.

## Migration and deployment finding

The database reached through `docker-compose.prod.yml` currently reports:

- applied through `diagnostics.0005`;
- `diagnostics.0006` through `0012` not applied;
- `users.0002` not applied.

The repository branches contain those unapplied migrations. New migrations must
be generated and tested against a disposable test database, but must not be
applied to the current production database until a reviewed rollout and backup
are prepared.

## Procedure authoring contract

The first authoring interface remains Django admin. Authors create a procedure
version, then its ordered operations. Each operation page owns three inline
collections: predecessor dependencies, evidence requirements, and reference
media.

Dependency rules are deliberately stricter than a generic directed graph:

- both operations must belong to the same procedure version;
- a dependency may point only to a lower sequence number;
- the admin selector shows only eligible predecessors;
- model validation rejects invalid interactive or programmatic writes;
- publication revalidates the complete stored graph so bulk/import paths cannot
  bypass the invariant.

This ordering rule makes cycles impossible and keeps the mechanic workflow
deterministic. Published versions remain immutable.

For a safe local walkthrough, run:

```bash
python manage.py seed_assurance_demo
```

The seed is idempotent and creates fictional demonstration data carrying an
explicit non-OEM disclaimer. It must not be treated as repair information or
loaded into production without a separate deployment decision.

## Evidence file security and retention

Evidence files are validated synchronously before Django writes them to media
storage. The acceptance pipeline is fail-closed:

1. reject files above `ASSURANCE_EVIDENCE_MAX_FILE_SIZE` (25 MB by default);
2. identify PDF, JPEG, PNG, MP4, or UTF-8 text from content bytes;
3. enforce the format allowlist for the selected evidence type;
4. reject a mismatch between declared and detected MIME type;
5. stream the file to ClamAV over its `INSTREAM` protocol;
6. store the SHA-256 digest and security result in immutable evidence metadata.

An unavailable scanner, malware finding, or ambiguous scanner response rejects
the upload. The production Compose definition provides an isolated ClamAV
service and persistent signature database; it does not expose ClamAV publicly.

Evidence is append-only and retained for the configured policy period (2,555
days / seven years by default). The retention value is copied into each file's
security metadata so later policy changes remain auditable. Automated deletion
is intentionally not enabled: legal hold, completed repair records, and future
supersession rules must be evaluated before any purge workflow is introduced.
Uploaded evidence remains under `runtime/media/assurance/evidence/`; production
backup and restore must cover that volume together with PostgreSQL.

## Evidence supersession

Evidence correction never updates or deletes the original row. An authorized
technician selects the current evidence, supplies a replacement with the same
operation, requirement, and evidence type, and records a mandatory reason.
The replacement points to the previous row through `supersedes`.

Only one direct replacement is allowed for a row, enforced both under a
transactional row lock and by a conditional database uniqueness constraint.
Further correction continues from the latest row, producing a linear,
attributable chain rather than competing branches.

Completion gates, measurement range checks, and expert decisions use only leaf
evidence that has not been superseded. The full chain remains visible in the
case UI, audit events, and immutable repair-record snapshot. Supersession is
allowed only while the operation can accept evidence; completed or locked
operations must first enter a future controlled rework/exception workflow.

## Case cancellation and operation exceptions

Skipping a procedure operation is an authorization decision, not an ordinary
technician status change. Only a senior technician or technical manager from
the case organization can skip an available or in-progress operation, and only
when the published procedure explicitly permits escalation. A mandatory
rationale is stored in an append-only, one-to-one
`CaseOperationException` record with its authorizer and timestamp.

An approved skip is terminal for that execution and satisfies dependency
unlocking and verification gates. The exception remains explicit in the case
UI, audit trail, operation result, and immutable repair-record snapshot; a
plain skipped status without the authorization record never satisfies a
mandatory verification gate.

Case cancellation uses the same senior-or-manager authority and requires a
reason. It closes every unfinished execution as skipped, records the affected
operations in the case audit event, and marks the case cancelled. Completed
work and all previously captured evidence remain intact. Completed and
cancelled cases reject further evidence, operation decisions, completion, or
verification.

## Remote expert-review notifications

Moving an operation to `requires_review` writes one durable notification per
eligible reviewer in the same database transaction. Recipients must be active,
belong to the repair-case organization, have a non-empty email address, meet
the operation's minimum approval role, and be different from the technician
who completed the operation. The copied recipient address and request
timestamp preserve what was routed at that moment.

The uniqueness of operation, recipient, and review-request timestamp makes
queueing idempotent while allowing a new notification after a rework cycle.
An `expert_review_queued` audit event records the number of routable
recipients, including zero so missing reviewer configuration is visible.

The dedicated `assurance-notifier` process drains the transactional outbox
every 30 seconds. It uses row locking with skip-locked semantics so multiple
workers cannot deliver the same item concurrently. Delivery status, attempt
count, last error, next retry time, and sent time are retained. Failures use
bounded exponential backoff and stop automatically after five attempts.

Email delivery uses the existing Django email configuration.
`ASSURANCE_REVIEW_BASE_URL` supplies the public origin for the case link and
must be set in production together with the SMTP variables. No email is sent
inside the repair operation transaction.

## Audit inspection and export

The case audit screen is a read-only projection of append-only
`RepairAuditEvent` rows. It presents newest events first, resolves the actor
and operation for human review, shows status transitions and payload details,
and paginates at 50 events. Reviewers can filter by exact event action and by
case-operation execution.

Access is limited to active senior experts, technical managers, and auditors
inside the case organization; superusers retain operational access. Junior
technicians cannot open the screen or export its data. Organization scoping is
applied before resolving the requested case, preventing identifiers from being
used to cross tenant boundaries.

CSV and JSON downloads contain the same filtered event selection. Each record
includes the immutable event identifier and timestamp, action, operation key,
actor identity, before/after states, and structured payload. Downloads use an
attachment filename tied to the repair case and set `nosniff`. Exports are
audit projections only: they do not mutate the case, evidence, decisions, or
the immutable repair record.

## External Repair Certificate

Every immutable `RepairRecord` receives a random UUID public identifier. The
certificate route resolves only that identifier; sequential case and record
IDs are never accepted. Existing records receive independent UUID values
during migration.

The certificate is generated exclusively from the immutable repair-record
snapshot and checksum. It shows the vehicle make, model, year, masked VIN,
procedure name and pinned version, verification result, operation status and
completion time, active evidence count, approved-exception indicator, record
timestamp, and SHA-256 integrity value.

The projection deliberately excludes the full VIN, database identifiers,
technician and reviewer identities, evidence files and hashes, measurements,
free-text results, internal rationales, and audit payloads. It also states that
the certificate is neither a warranty nor an OEM endorsement.

The URL is publicly shareable but treated as an unlisted capability link.
Responses set `noindex, nofollow, noarchive`, `no-referrer`, and `nosniff`
headers. Unknown UUIDs return 404. The internal case screen exposes the link
only after the verified repair record exists.

## First implementation slice

The first slice will:

1. create the independent `assurance` app;
2. add the minimal domain schema;
3. implement procedure publication and case instantiation;
4. implement operation availability, evidence gates, approval gates,
   verification, and append-only audit;
5. prove one complete multi-user repair in automated tests;
6. expose procedure authoring through Django admin and a minimal mechanic view.

This is intentionally not a CRM, DMS, AI engine, content scraper, or HR system.
