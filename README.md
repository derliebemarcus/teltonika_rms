# Teltonika RMS Home Assistant Integration

Custom Home Assistant integration for read-only monitoring of Teltonika RMS managed devices.

The integration connects to the RMS API, discovers your devices, and creates Home Assistant entities for connectivity, diagnostics, timestamps, and optional location tracking.

## What This Component Provides

- Authentication with either:
  - OAuth2 (authorization code + PKCE)
  - Personal Access Token (PAT)
- Device polling with request-budget safeguards (RMS monthly quota aware)
- API envelope parsing (`success`, `data`, `errors`, `meta`)
- Status-channel handling (`meta.channel`) with Socket.IO first, HTTP polling fallback
- Per-device entities:
  - `binary_sensor`: online connectivity
  - `sensor`: model, firmware, serial, last seen timestamp
  - `device_tracker` (optional): GPS location only for devices that provide coordinates, including detailed location attributes (`location_detail`, `coordinates`, `google_maps_url`)
- Service:
  - `teltonika_rms.refresh` to trigger immediate refresh

## Installation

### Option 1: Install with HACS

1. Open HACS in Home Assistant.
2. Go to Integrations.
3. Add this repository as a Custom Repository (type: `Integration`).
4. Search for `Teltonika RMS`.
5. Install and restart Home Assistant.

### Option 2: Manual Installation

1. Copy this folder to your Home Assistant config:
   - `/config/custom_components/teltonika_rms`
2. Ensure files like `manifest.json` and `__init__.py` are directly inside that folder.
3. Restart Home Assistant.

## Credentials Setup

### OAuth2 (recommended)

1. Log in to RMS.
   - Open [RMS](https://rms.teltonika-networks.com/).
   - Sign in with the RMS account that owns the devices you want to monitor.
   - Complete two-factor authentication if your account requires it.
2. Create an OAuth application in [RMS Developers](https://developers.rms.teltonika-networks.com/).
3. Configure callback URL:
   - `https://<your-home-assistant-url>/auth/external/callback`
4. In Home Assistant, go to:
   - `Settings -> Devices & Services -> Application Credentials`
5. Add `Teltonika RMS` credentials (client ID + client secret).

### Personal Access Token (PAT)

1. Log in to RMS.
   - Open [RMS](https://rms.teltonika-networks.com/).
   - Sign in with the RMS account that owns the devices you want to monitor.
   - Complete two-factor authentication (required for PAT generation).
2. In RMS, generate a Personal Access Token:
   - Open API token settings as described in [RMS API Credits](https://wiki.teltonika-networks.com/view/RMS_API_Credits).
   - Create a new token and copy it immediately.
3. Grant at least:
   - `devices:read`
4. Add these if needed:
   - `device_location:read` for GPS tracker entities
   - `device_actions:read` for broader status/channel visibility

## Configuration in Home Assistant

1. Go to `Settings -> Devices & Services -> Add Integration`.
2. Select `Teltonika RMS`.
3. Choose auth mode:
   - `OAuth2 (recommended)` or `Personal access token (PAT)`.
4. Finish authentication.
5. Open integration options to tune:
   - Inventory polling interval
   - State polling interval
   - Device count estimate
   - Optional tag/status filters
   - Enable/disable location tracker entities
   - Optional `spec_path` (compiled OpenAPI YAML on HA filesystem)

## Endpoint Matrix

- Runtime endpoint matrix is loaded from `spec_path` when configured.
- If unavailable or invalid, bundled `endpoint_matrix_frozen.json` is used.
- Regenerate bundled matrix from OpenAPI YAML:

```bash
python3 tools/generate_rms_endpoint_matrix.py /path/to/compiled.yaml
```

## Conventions and Tests

- Development conventions are aligned with Home Assistant custom integration guidance:
  - [Home Assistant Developer Docs](https://developers.home-assistant.io/docs/development_index/)
- Translation consistency can be validated with:

```bash
python3 tools/check_translations.py
```

- Test suite follows HA-style layout under:
  - `tests/components/teltonika_rms/`

- Run tests with:

```bash
python3 -m pytest
```

Hinweis: Für den vollständigen Testlauf wird eine Home-Assistant-Entwicklungsumgebung benötigt
(siehe Developer Docs), da Integrationsmodule `homeassistant.*` importieren.

- Release notes are tracked in:
  - `CHANGELOG.md`

## Git Hooks and Version Tags

Install repository hooks once:

```bash
tools/install_git_hooks.sh
```

`pre-commit` hook behavior:

- Runs the full test suite (`python3 -m pytest --maxfail=0`)
- Always prints per-test summary with:
  - test name
  - duration
  - result
- Blocks commit when at least one test fails
- Requires a test environment where integration imports resolve (Home Assistant dev dependencies installed)

`pre-push` hook behavior:

- Ensures a version tag `v<manifest.version>` exists before push
- Ensures the tag is part of current branch history

Create a release tag for the current version:

```bash
tools/create_version_tag.sh
git push --follow-tags
```
