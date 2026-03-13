# Changelog

All notable changes to this project are documented in this file.

## 0.6.0 - 2026-03-13

### New Features

- Added new optional RMS sensors that are created only when the API actually provides the value:
  - clients count
  - router uptime
  - signal strength
  - WAN state
  - connection state
  - connection type
  - SIM slot
- Added representative RMS contract fixtures derived from the compiled API schema to validate payload handling against more realistic examples.

### Improvements

- Expanded diagnostics output with auth mode, aggregate-state availability, and monthly request estimate to make support cases easier to debug.
- Added repository quality gates for commit-message format and release-note structure so project rules are enforced in CI, not only by local hooks.
- Added issue templates, a pull-request template, and maintainer contribution guidance to make incoming changes and bug reports more actionable.

### Changes

- Updated README to document the new RMS sensors and clarify that they are only exposed when RMS provides the underlying value.
- Added repository-level governance tooling:
  - `tools/check_commit_messages.py`
  - `tools/check_release_notes.py`
  - `.github/workflows/quality.yml`

### Bugfixes

- Fixed OAuth2 reauthentication flow so it correctly restarts implementation selection instead of calling a non-existent superclass reauth method.

## 0.5.2 - 2026-03-13

### New Features

- None.

### Improvements

- Added repository-level `icon.png` compatibility branding alongside `brand/icon.png` so HACS can resolve the integration icon more reliably.
- Raised automated test coverage to 97%, giving stronger regression protection for config flow, coordinators, API fallback paths, and repository metadata.
- Added enforcement for structured release notes so GitHub releases consistently highlight product impact first and maintenance/testing items afterwards.

### Changes

- Standardized README badges so all top-level badges use a consistent `for-the-badge` height and styling.
- Enforced categorized commit-message bodies through a `commit-msg` hook:
  - `add:`
  - `change:`
  - `deprecate:`
  - `remove:`
  - `fix:`

### Bugfixes

- Fixed OAuth2 reauthentication to restart implementation selection correctly instead of calling a non-existent superclass reauth method.
- Replaced the unstable dynamic license badge with a stable MIT badge so the repository page no longer shows `repo not found`.

## 0.5.1 - 2026-03-13

### New Features

- None.

### Improvements

- Increased automated test coverage to 94% across the integration codebase, improving regression protection for authentication, coordinator updates, and status-channel handling.
- Expanded runtime coverage for RMS API retries, pagination, aggregate-state fallback, and channel resolution so remote-device state handling is validated more thoroughly.
- Expanded unit coverage for endpoint-matrix parsing and device normalization helpers, reducing the chance of API-schema or payload-shape regressions.

### Changes

- Kept the Coveralls workflow aligned with the current HA/runtime dependency floor so published coverage stays current and comparable across releases.

### Bugfixes

- None.

## 0.5.0 - 2026-03-13

- Added README badges for HACS, GitHub releases, license, and downloads.
- Expanded OAuth setup documentation:
  - `my.home-assistant.io` link requirement is now documented explicitly.
  - RMS OAuth redirect URL is documented as `https://my.home-assistant.io/redirect/oauth`.
  - Post-credential setup steps in Home Assistant are documented more clearly.
- Simplified integration branding assets to a single local icon:
  - kept `brand/icon.png`
  - removed unused logo and dark-variant files
- Raised the minimum supported Home Assistant version to `2026.3.0`:
  - aligns with local brand icon support for custom integrations
  - mirrored in both `manifest.json` and `hacs.json`
- Added a metadata consistency test to keep `manifest.json` and `hacs.json` aligned.

## 0.4.0 - 2026-03-11

- Updated integration metadata documentation URL:
  - Home Assistant "help/documentation" link now points to the project repository:
    - `https://github.com/derliebemarcus/teltonika_rms`

## 0.3.1 - 2026-03-11

- Refined test execution split:
  - Added `tests/unit/` for pure unit tests that run without Home Assistant dependencies.
  - Added `tests/ha/` for Home Assistant-dependent tests.
- Updated `pre-commit` hook behavior:
  - Without `homeassistant` installed: runs all unit tests.
  - With `homeassistant` installed: runs unit + HA test suites.
  - Keeps `--maxfail=0` and blocks commit only after all selected tests completed.
- Added HA-test marker configuration in `pytest.ini`.
- Refactored integration module imports in `__init__.py` to avoid importing heavy HA/runtime dependencies at module import time, improving testability outside HA.

## 0.3.0 - 2026-03-11

- Added versioned repository Git hooks (`.githooks`):
  - `pre-commit` runs all tests, prints per-test name/duration/result, and blocks commit on failures.
  - `pre-push` enforces an existing release tag `v<manifest.version>`.
- Added tooling scripts:
  - `tools/install_git_hooks.sh`
  - `tools/print_pytest_summary.py`
  - `tools/create_version_tag.sh`
- Extended location normalization to detect more coordinate formats (`lat/lng`, `lon`, GeoJSON coordinate arrays, coordinate strings).
- Device tracker now exposes explicit location attributes:
  - `location_detail`
  - `coordinates`
  - `google_maps_url`

## 0.2.0 - 2026-03-11

- Added dual authentication modes:
  - OAuth2 (Authorization Code + PKCE)
  - Personal Access Token (PAT)
- Added PAT reauthentication flow.
- Added diagnostics endpoint with token redaction.
- Added HACS metadata and Python-specific `.gitignore`.
- Switched `last_seen` from `datetime` entity to `sensor` timestamp entity.
- Ensured device tracker entities are only created when valid coordinates exist.
- Added and localized translation files for EU languages and additional requested languages.
- Expanded README:
  - Installation via HACS and manual copy
  - Configuration flow
  - Detailed credential setup steps for OAuth2 and PAT
- Added endpoint matrix tooling and regenerated frozen matrix support.
- Added issue tracker URL in manifest and bumped integration version to `0.2.0`.

## 0.1.0 - 2026-03-11

- Initial custom integration scaffold for Teltonika RMS.
- OAuth2 config flow, API client, coordinators, and basic entities.
- Request budget estimation and channel-status fallback support.
