# AGENTS.md

## Purpose

This repository contains a custom Home Assistant integration for Teltonika RMS.
The project is expected to stay close to Home Assistant conventions while keeping
strict QA, release, and dependency hygiene.

## Primary Objectives

- Keep the integration stable for Home Assistant users.
- Preserve request-budget awareness for RMS API usage.
- Only expose entities and controls that are actually supported by RMS data or capabilities.
- Maintain strong automated quality gates.
- Ensure released versions match the real security and dependency state on `main`.

## Repository Structure

- `__init__.py`: integration setup, runtime wiring, platform forwarding
- `config_flow.py`: OAuth2/PAT config and options flow
- `api.py`: RMS transport, retry logic, channel resolution, write actions
- `coordinator.py`: inventory, state, port scan, port configuration coordinators
- `models.py`: RMS payload normalization
- `binary_sensor.py`, `sensor.py`, `device_tracker.py`, `button.py`, `switch.py`, `update.py`: entity platforms
- `diagnostics.py`: support diagnostics and redaction
- `endpoint_matrix_frozen.json`: bundled endpoint matrix fallback
- `tests/unit/`: tests that run without Home Assistant runtime dependencies
- `tests/ha/`: Home Assistant-aware runtime tests
- `tools/`: project-specific validation and release tooling

## Architectural Rules

- Prefer existing coordinator and API abstractions over adding one-off logic.
- New RMS features must fit the existing transport/coordinator/entity model.
- Optional features must never block base integration setup.
- RMS features that require asynchronous status channels must support Socket.IO first and HTTP fallback second.
- Keep RMS envelope parsing consistent: `success`, `data`, `errors`, `meta`.
- Keep the endpoint-matrix approach intact:
  - runtime matrix via `spec_path`
  - fallback matrix via `endpoint_matrix_frozen.json`

## Home Assistant Rules

- Follow Home Assistant integration conventions as closely as possible.
- Prefer config-flow-first behavior.
- Keep diagnostics available and useful.
- Only create entities when backing RMS data is actually present.
- Keep metadata, translations, branding, and manifest aligned with Home Assistant expectations.
- Do not regress importability or HA integration lifecycle behavior.

## Entity Rules

- Create entities only when RMS provides the underlying data or capability.
- `device_tracker` entities must only exist for devices with real coordinates.
- PoE `switch` entities must only exist for ports with `poe_enable`.
- Firmware `update` entities must only exist when RMS exposes usable firmware metadata.
- Do not expose speculative entities based only on model guesses.

## Scope and Permission Rules

- Any new RMS feature must be checked for required OAuth/PAT scopes.
- If a feature introduces a new scope, the change must include:
  - a success-path test
  - a missing-scope test
  - proof that the base integration still starts when the feature is optional
- Scope changes must also update:
  - README setup instructions
  - runtime warnings or error messages
  - any relevant flow or options behavior

## API and Write-Action Rules

- Only implement write actions when the RMS path, method, payload, and response behavior are well established.
- For control actions, prefer real RMS payload validation over assumptions.
- Preserve retry and backoff behavior for RMS API calls.
- Preserve request-budget safeguards and coordinator cadences.

## Testing Rules

- Coverage must not decrease.
- The enforced floor is `97.1%`.
- High coverage is necessary but not sufficient; tests must lock intended behavior.
- New optional features must degrade gracefully when:
  - data is missing
  - the capability is not available
  - the required scope is missing
- Changes to setup, reauth, optional features, and feature degradation paths need explicit runtime tests.
- Keep tests split appropriately:
  - `tests/unit/`
  - `tests/ha/`

## QA and CI Rules

- The following checks are part of repository quality and must stay healthy:
  - `Tests and Coverage`
  - `Quality Gates`
  - `CodeQL`
  - `Security Gates`
  - `Publish Release`
- Additional repository QA includes:
  - `Dependency Review`
  - `Mutation Testing`
  - Dependabot updates
- Any CI/workflow change should be locally sanity-checked before push.

## Static Analysis and Security Rules

- Keep these clean:
  - `ruff check .`
  - `ruff format --check .`
  - `mypy .`
  - `actionlint`
- Security tooling currently includes:
  - `pip-audit`
  - `gitleaks`
  - `CodeQL`
  - Dependabot
- Security-related dependency updates on `main` should result in a release if they affect shipped runtime behavior.

## Dependency Rules

- Runtime dependencies belong in `manifest.json`.
- Development and CI dependencies belong in `requirements-dev.txt`.
- Static-analysis and mutation-tool configuration belongs in `pyproject.toml`.
- Keep hooks, workflows, and manifests aligned when dependency versions change.
- Do not leave a runtime dependency newer in CI than in the shipped manifest if users are expected to benefit from that fix.

## Hook Rules

### `pre-commit`

- Must run all tests, regardless of early failures.
- Must print a per-test summary.
- Must block the commit on test failure.
- Must enforce the coverage floor.

### `commit-msg`

- Default rule:
  - single-line messages must start with `add:`, `change:`, `deprecate:`, `remove:`, or `fix:`
  - multi-line messages must have:
    - a short summary
    - a blank line
    - categorized body lines
- Explicit bypasses:
  - commits authored or committed by `dependabot[bot]`
  - commit messages whose first meaningful line starts with:
    - `Update`
    - `Bump`
    - `Merge`
- These bypass prefixes are case-sensitive and must start with an uppercase first letter.
- When a bypass applies, the rest of the commit message is not validated.

## Commit Message Rules for Human/Agent Commits

- Prefer normal repository commit rules unless a documented bypass applies.
- Multi-line commit format:
  - line 1: short summary
  - line 2: blank
  - remaining lines: exactly one category prefix per line
- Keep commit messages factual and scoped to the real change.

## Versioning Rules

- Semantic versioning is mandatory:
  - patch: fixes, compatibility, diagnostics, documentation, testing, security/dependency release updates
  - minor: new entities, services, or user-visible capabilities without breaking configuration
  - major: breaking configuration or behavior changes
- The agent should proactively recommend a version bump when warranted.
- The agent should briefly justify why patch/minor/major is appropriate.

## Release Rules

- Every published version must have:
  - matching `manifest.json` version
  - matching changelog section
  - matching git tag `v<version>`
  - GitHub release entry
- Release publishing is triggered via `tools/publish_release.sh`.
- GitHub Actions create/update the GitHub release only after required checks succeed.
- Do not retarget or move existing release tags.
- If security-relevant updates were merged to `main`, publish a follow-up patch release.

## Release Notes Rules

- Changelog entries must use these headings in this order:
  - `### New Features`
  - `### Improvements`
  - `### Changes`
  - `### Bugfixes`
- Put user-visible product impact first.
- Put testing/pipeline/governance changes after product-relevant items.
- Use `CHANGELOG.md` as the source of truth for release notes.

## Documentation Rules

- Keep README accurate for:
  - features
  - scopes
  - OAuth2/PAT setup
  - HACS/manual installation
  - reauthentication guidance after scope changes
- Keep the manifest documentation link pointed at the GitHub repository.

## Branding Rules

- `brand/` should contain only `brand/icon.png`.
- Root `icon.png` exists as the HACS compatibility fallback and should remain aligned.
- Do not break HACS or Home Assistant icon behavior.

## Translation Rules

- German is the reference language.
- Translation key sets must remain aligned.
- Placeholder and artifact checks must remain clean.

## Live RMS Validation Rules

- For RMS control/configuration features, prefer real RMS payload validation when available.
- Use live API validation carefully and avoid committing secrets or tokens.
- Treat tokens and cookies as sensitive even if shared during debugging.

## Practical Agent Workflow

Before pushing meaningful code changes, verify:

- `ruff check .`
- `ruff format --check .`
- `mypy .`
- `pytest`
- coverage threshold

For workflow or release-process changes, also verify:

- workflow structure is internally consistent
- release gating still points to the correct required workflows
- dependency/security jobs use a compatible Python version

## Anti-Rules

Do not:

- create entities without real backing data
- let optional features block setup
- lower coverage or quality gates
- change release tags retroactively
- ship scope changes without tests and documentation
- leave security-relevant dependency changes unreleased when they affect users
- trigger a reboot of a device without user consent
- trigger any switch without user consent

## Rules added by user

When testing against the OpenAPI:
 - If the permissions from key PAT_0.8.4_Permissions do not allow to aquire an information, fall back to key PAT_All_Read_Permissions. As a next step, detect the permission necessary to aquire the information.

For releases:
 - We distinguish between beta and productions releases.
 - Beta releases shall be marked in GitHub as pre-release.
 - The latest production release shall e marked in GitHub as latest release.
