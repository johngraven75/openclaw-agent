# Repository Engineering Standard

Mandatory for all AI-assisted engineering. Before code define product goal, target user, measurable success criteria, non-goals, assumptions and missing requirements; propose architecture covering platform constraints, security, contracts, persistence, lifecycle, observability, compatibility, upgrades and rollback. Organize work/reporting as **Frontend**, **Connector / integration**, and **Backend** where applicable.

Break work into independently testable vertical slices suitable for isolated worktrees/branches. Define exact files, public interfaces, validation/error handling, logging/telemetry, security implications and definition of done. Keep commits atomic/conventional and never merge around failing required checks.

Ship fresh idiomatic production code following SOLID/DRY, explicit types, immutable data where practical, dependency injection, secure defaults, validation, null safety, cancellation/disposal and separation of concerns. No TODOs, placeholders, fabricated integrations, credentials or incomplete production paths. Preserve backward compatibility unless migration is explicitly approved.

Every slice requires appropriate unit, integration, contract, security, performance-budget and manual QA validation. Run all relevant formatting/lint/static/type/unit/integration/E2E/package checks. Self-review races, deadlocks, leaks, disposal, retries, lifecycle cleanup, privileges, interrupted operations and rollback.

Production readiness requires diff summary, changelog, migration notes, API/config/environment docs, rollback plan, monitoring plan, test evidence and artifact checksums where applicable. Commit changes before building; rerun after fixes; never claim unverified completion/publication/signing/test success.
