# LOW_PRIORITY_TASKS

## Remove redundant `from __future__ import annotations` (Python 3.14)

### Why this is low priority
- We now run on Python 3.14, where deferred annotation behavior is the default.
- `from __future__ import annotations` is generally redundant in this codebase.
- Keeping it does not break runtime behavior, so this is cleanup rather than a functional fix.

### Goal
Remove redundant `from __future__ import annotations` imports to reduce legacy noise while preserving behavior.

### Scope
- Apply only to first-party Python modules in this repo.
- Skip vendored, generated, and third-party snapshot code.

### Plan
1. Inventory: list all files containing `from __future__ import annotations`.
2. Safety pass: identify any modules where runtime introspection of raw annotation objects is relied on; flag those for manual review.
3. Mechanical cleanup: remove the future import from safe files.
4. Validation: run test suite and lint/type checks.
5. Rollout: land as one cleanup PR (or split by package if diff is too large).

### Acceptance criteria
- No remaining redundant `from __future__ import annotations` in in-scope files.
- Tests pass after removal.
- Lint/type checks pass after removal.
- No runtime regressions in annotation-dependent paths.

### Implementation notes
- Prefer an automated codemod/script for deterministic edits.
- Keep this isolated from feature work to simplify review.
- If any file depends on legacy annotation string behavior for reflection, document and exempt it explicitly.

## Docstring quality and consistency sweep

### Why this is low priority
- Current docstring issues are mostly readability and maintenance quality concerns, not functional bugs.
- Inconsistent docstring style increases noise but does not usually block runtime behavior.
- This can be done incrementally without affecting feature delivery.

### Goal
Audit first-party code for poor, missing, or incorrect docstrings and align docstrings to describe purpose (why code exists), not type information or step-by-step behavior narration. Remove module-level docstrings.

### Scope
- Apply to first-party source files across the repo.
- Skip vendored, generated, and third-party snapshot code.
- Include functions, methods, classes, and significant internal helpers.
- Exclude module-level docstrings from the target style; remove existing ones unless explicitly required by tooling.

### Plan
1. Inventory: scan for existing docstrings and identify missing docstrings for in-scope symbols.
2. Quality pass: flag docstrings that restate types, mirror signatures, or only describe mechanics without intent.
3. Rewrite pass: update docstrings to concise purpose-first language focused on responsibility and intent.
4. Module cleanup: remove module-level docstrings and keep file-level context in code comments only when strictly needed.
5. Validation: run lint/tests and any docstring-related tooling checks to ensure no regressions.

### Acceptance criteria
- In-scope functions, methods, and classes have docstrings where expected by project conventions.
- Docstrings are purpose-focused and avoid duplicating type/signature information.
- Incorrect or misleading docstrings are corrected.
- Module-level docstrings are removed from in-scope files (unless a documented tooling exception exists).
- Lint/tests pass after changes.

### Implementation notes
- Prefer scripted detection for baseline findings, followed by targeted manual rewrites.
- Keep edits behavior-neutral; this is documentation quality work only.
- Record any explicit exceptions (for tooling or third-party integration) in the PR description.

## Drift-guard assertion extraction into dedicated monitor tests

### Why this is low priority
- Existing drift checks are defensive and useful, but placement is mainly an architecture/maintenance concern rather than an immediate functional defect.
- Moving these checks improves test organization and intent clarity without changing product behavior.
- This work is best done as a focused cleanup sweep to avoid mixing with feature delivery.

### Goal
Find drift-pattern assertions embedded in runtime modules and move coverage into domain-specific unit tests located in dedicated drift-monitor suites (for example `test_monitor_drift`), separated from standard functionality tests.

### Scope
- Apply to first-party source and tests in this repo.
- Focus on invariant/synchronization checks such as enum-to-map sync, registry parity, and exhaustive key coverage assertions.
- Exclude true runtime safety checks that must remain in startup/runtime codepaths.
- Keep drift-monitor tests separate from existing behavior/feature test modules.

### Plan
1. Inventory: scan codebase for drift-pattern checks (assertions and explicit mismatch guards) in runtime modules.
2. Classification pass: separate checks that are developer-maintenance invariants from checks that are required runtime safety guarantees.
3. Test extraction: implement dedicated domain-specific drift tests under a monitor-style layout (for example `tests/**/test_monitor_drift/`).
4. Runtime cleanup: remove or reduce in-module defensive assertions that are now covered by drift tests, while preserving required runtime fail-fast checks where justified.
5. Validation: run targeted and full test suites to ensure no behavior regressions.

### Acceptance criteria
- Drift-pattern invariant checks are discoverable in dedicated monitor drift test suites, not mixed into standard functionality tests.
- Each extracted invariant has clear test coverage and fails with actionable mismatch details.
- Runtime modules no longer contain redundant drift assertions unless explicitly required for production safety.
- Tests pass after refactor.

### Implementation notes
- Prefer reusable helpers/fixtures for common drift checks to keep assertions consistent across domains.
- Use descriptive naming so monitor tests are easy to locate (e.g., `test_monitor_drift_*`).
- Document any invariants intentionally kept as runtime checks and the reason they cannot be test-only.
