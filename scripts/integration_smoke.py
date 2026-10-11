#!/usr/bin/env python3
import hashlib
import hmac
import sys
import time
import uuid

import requests

LABELS_PATH = "/api/v1/shipments/labels"


def sign(method, path, body_bytes, token, timestamp, nonce):
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f"{method}\n{path}\n\n{timestamp}\n{nonce}\n{body_hash}\n"
    digest = hmac.new(
        token.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def main():
    if len(sys.argv) != 3:
        print("Usage: integration_smoke.py <gateway_base_url> <api_token>", file=sys.stderr)
        sys.exit(2)
    base = sys.argv[1].rstrip("/")
    token = sys.argv[2]

    health = requests.get(f"{base}/healthz", timeout=15)
    health.raise_for_status()
    print("healthz:", health.json())

    body_bytes = b"{}"
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    sig = sign("POST", LABELS_PATH, body_bytes, token, ts, nonce)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-SC-Timestamp": ts,
        "X-SC-Nonce": nonce,
        "X-SC-Signature": sig,
    }
    r = requests.post(f"{base}{LABELS_PATH}", data=body_bytes, headers=headers, timeout=30)
    payload = r.json() if r.content else {}
    print("labels:", r.status_code, payload)
    if r.status_code == 401:
        print("FAIL: token rejected", file=sys.stderr)
        sys.exit(1)
    if payload.get("error_code") != "invalid_payload":
        print("FAIL: expected invalid_payload for empty body", file=sys.stderr)
        sys.exit(1)
    print("Integration smoke OK")


if __name__ == "__main__":
    main()
