#!/usr/bin/env bash
# Build shipping_hub_connector.zip for customer distribution (run from odoo-addons/).
set -euo pipefail
MODULE="shipping_hub_connector"
OUT_DIR="${1:-dist}"
mkdir -p "$OUT_DIR"
ZIP="$OUT_DIR/${MODULE}.zip"
rm -f "$ZIP"
zip -r "$ZIP" "$MODULE" \
  -x "${MODULE}/.git/*" \
  -x "${MODULE}/*__pycache__/*" \
  -x "${MODULE}/*.pyc" \
  -x "${MODULE}/.DS_Store" \
  -x "${MODULE}/*/.DS_Store" \
  -x "${MODULE}/scripts/*" \
  -x "${MODULE}/*.bak"
echo "Created: $ZIP"
unzip -l "$ZIP" | tail -5
