#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
MARKER_START="# >>> teltonika-rms auto-pip >>>"
MARKER_END="# <<< teltonika-rms auto-pip <<<"

install_hook() {
  local activate_file="$1"

  if [ ! -f "$activate_file" ]; then
    return
  fi

  if grep -Fq "$MARKER_START" "$activate_file"; then
    return
  fi

  cat >>"$activate_file" <<EOF

$MARKER_START
if [ -n "\${VIRTUAL_ENV:-}" ] && [ -x "\$VIRTUAL_ENV/bin/python" ]; then
    "\$VIRTUAL_ENV/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
fi
$MARKER_END
EOF
}

install_hook "$ROOT/.venv/bin/activate"
install_hook "$ROOT/.venv-test/bin/activate"
