#!/usr/bin/env bash
# Wrapper: export SHIPPING_HUB_* e execute install.sh após upgrade manual, ou use odoo shell.
set -euo pipefail
echo "Use SHIPPING_HUB_API_TOKEN + SHIPPING_HUB_GATEWAY_URL com shipping_hub_connector/install.sh"
echo "(configure_odoo_hub_gateway corre automaticamente se SHIPPING_HUB_API_TOKEN estiver definido)."
echo "Exemplo:"
echo "  export SHIPPING_HUB_GATEWAY_URL=https://stip.pt/hub-test"
echo "  export SHIPPING_HUB_API_TOKEN=<token>"
echo "  SHIPPING_HUB_NONINTERACTIVE=1 ./shipping_hub_connector/install.sh"
