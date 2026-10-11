#!/usr/bin/env bash
set -euo pipefail
GATEWAY_URL="${SHIPPING_HUB_GATEWAY_URL:-https://stip.pt/hub-test}"
PROVISION_KEY="${ODOOCARRIERS_PROVISION_KEY:-}"
IAP_TOKEN="${1:-test-iap-$(openssl rand -hex 8)}"
headers=(-H "Content-Type: application/json")
if [[ -n "${PROVISION_KEY}" ]]; then
  headers+=(-H "X-OdooCarriers-Provision-Key: ${PROVISION_KEY}")
fi
payload=$(printf "{\"iap_account_token\":\"%s\",\"plan_code\":\"free\"}" "${IAP_TOKEN}")
echo "Gateway: ${GATEWAY_URL}"
response=$(curl -sS -X POST "${GATEWAY_URL%/}/api/v1/accounts/provision" "${headers[@]}" -d "${payload}")
echo "${response}" | python3 -m json.tool
api_token=$(echo "${response}" | python3 -c "import sys,json; print(json.load(sys.stdin).get(\"api_token\",\"\"))")
if [[ -z "${api_token}" ]]; then exit 1; fi
echo "API token: ${api_token}"
