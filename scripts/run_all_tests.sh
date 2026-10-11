#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATEWAY="${ROOT}/hub-gateway"
VENV="${GATEWAY}/.venv"

log() { echo "==> $*"; }
fail() { echo "ERROR: $*" >&2; exit 1; }

[[ -d "${GATEWAY}" ]] || fail "Missing hub-gateway"

if [[ ! -x "${VENV}/bin/python" ]]; then
  log "Creating hub-gateway virtualenv..."
  python3 -m venv "${VENV}"
fi

log "Installing dependencies..."
"${VENV}/bin/pip" install -q -r "${GATEWAY}/requirements-dev.txt"
"${VENV}/bin/pip" install -q requests

log "Hub Gateway — pytest"
(
  cd "${GATEWAY}"
  "${VENV}/bin/pytest" -v --tb=short "$@"
)

log "Odoo Shipping Hub Client — pytest"
(
  cd "${ROOT}/tests/connector"
  "${VENV}/bin/pytest" -v --tb=short --confcutdir=. . "$@"
)

if [[ -n "${SHIPPING_HUB_GATEWAY_URL:-}" ]] && [[ -n "${ODOOCARRIERS_API_TOKEN:-}" ]]; then
  log "Live integration smoke"
  "${VENV}/bin/python" "${ROOT}/scripts/integration_smoke.py" \
    "${SHIPPING_HUB_GATEWAY_URL}" "${ODOOCARRIERS_API_TOKEN}"
else
  log "Skipping live integration (set SHIPPING_HUB_GATEWAY_URL + ODOOCARRIERS_API_TOKEN)"
fi

log "All tests finished successfully."
