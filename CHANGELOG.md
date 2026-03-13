# Changelog

All notable changes to this project are documented in this file.

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
