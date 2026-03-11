# Teltonika RMS Home Assistant Integration

Custom Home Assistant integration for read-only Teltonika RMS monitoring with OAuth2 + PKCE.

## Features (v1)

- OAuth2 authentication (authorization code + PKCE)
- Device inventory and state refresh using `DataUpdateCoordinator`
- Request budget safeguards for RMS monthly quota
- RMS `meta.channel` handling with Socket.IO-first and HTTP polling fallback
- Redacted diagnostics support (`config_entry` diagnostics download)
- Entities per device:
  - Binary sensor: online
  - Datetime: last seen
  - Diagnostic sensors: model, firmware, serial
  - Optional device tracker: location
- Service: `teltonika_rms.refresh`

## Endpoint Matrix

- Runtime endpoint matrix is loaded from the options `spec_path` when set.
- If unavailable or invalid, the integration uses `endpoint_matrix_frozen.json`.
- You can regenerate the frozen matrix from a compiled OpenAPI document:

```bash
python3 tools/generate_rms_endpoint_matrix.py /path/to/compiled.yaml
```
