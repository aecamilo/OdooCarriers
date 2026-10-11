import json
import uuid
from decimal import Decimal
from typing import Any, Optional

from app.adapters.simulator import simulate_label
from app.config import settings
from app.db import db_cursor
from app.schemas.labels import LabelRequest
from app.services.quota_service import (
    check_quota,
    ensure_subscription_row,
    increment_labels_used,
    quota_snapshot,
)
from app.services.rate_limit_service import check_rate_limit


def validate_label_payload(data: dict) -> tuple[Optional[LabelRequest], str]:
    if not data:
        return None, "invalid_payload"
    try:
        req = LabelRequest.model_validate(data)
    except Exception:
        return None, "invalid_payload"
    if req.schema_version != "1.0" or req.operation != "create_shipment":
        return None, "invalid_payload"
    if not req.carrier_code or not req.reference:
        return None, "invalid_payload"
    if not req.shipper or not req.recipient or not req.parcels:
        return None, "invalid_payload"
    for p in req.parcels:
        if p.weight_kg <= 0:
            return None, "invalid_payload"
    return req, ""


def _total_weight(parcels) -> Decimal:
    return Decimal(str(sum(p.weight_kg for p in parcels)))


def find_idempotent_success(account_id: int, idempotency_key: str) -> Optional[dict]:
    if not idempotency_key:
        return None
    with db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT tracking_number, carrier_service, status
            FROM shipment_logs
            WHERE account_id = %s AND idempotency_key = %s AND status = 'success'
            LIMIT 1
            """,
            (account_id, idempotency_key),
        )
        row = cur.fetchone()
    if not row:
        return None
    return row


def create_label(account_id: int, data: dict) -> tuple[int, dict]:
    req, err = validate_label_payload(data)
    if not req:
        return 400, {"success": False, "error_code": err}

    sub = ensure_subscription_row(account_id)
    if sub["status"] not in ("active", "trialing"):
        return 403, {"success": False, "error_code": "subscription_inactive"}

    ok_rl, rl_err = check_rate_limit(account_id, sub["plan_code"])
    if not ok_rl:
        return 429, {"success": False, "error_code": rl_err}

    ok_q, q_err, is_overage = check_quota(sub)
    if not ok_q:
        return 429, {"success": False, "error_code": q_err}

    idem = req.idempotency_key or ""
    cached = find_idempotent_success(account_id, idem)
    if cached:
        sub = ensure_subscription_row(account_id)
        tracking = cached["tracking_number"] or ""
        _, label_b64, carrier_ref = simulate_label(req.carrier_code)
        return 200, {
            "success": True,
            "tracking_number": tracking,
            "label_base64": label_b64,
            "carrier_reference": carrier_ref,
            "quota": quota_snapshot(sub),
        }

    if settings.gateway_carrier_simulator or settings.app_debug:
        tracking, label_b64, carrier_ref = simulate_label(req.carrier_code)
    else:
        return 502, {
            "success": False,
            "error_code": "carrier_error",
            "error_detail": "Carrier adapter not configured; enable GATEWAY_CARRIER_SIMULATOR for tests.",
        }

    log_id = str(uuid.uuid4())
    yyyymm = sub["usage_yyyymm"]
    weight = _total_weight(req.parcels)
    with db_cursor() as (_, cur):
        try:
            cur.execute(
                """
                INSERT INTO shipment_logs (
                    id, account_id, usage_yyyymm, operation, order_reference,
                    idempotency_key, carrier_code, carrier_service, tracking_number,
                    status, http_status_code, error_code, parcels_count, total_weight_kg, is_overage
                ) VALUES (
                    %s, %s, %s, 'create_shipment', %s,
                    %s, %s, %s, %s,
                    'success', 200, NULL, %s, %s, %s
                )
                """,
                (
                    log_id,
                    account_id,
                    yyyymm,
                    req.reference,
                    idem or None,
                    req.carrier_code,
                    req.service_level,
                    tracking,
                    len(req.parcels),
                    weight,
                    1 if is_overage else 0,
                ),
            )
        except Exception:
            cached = find_idempotent_success(account_id, idem)
            if cached:
                sub = ensure_subscription_row(account_id)
                return 200, {
                    "success": True,
                    "tracking_number": cached["tracking_number"],
                    "label_base64": label_b64,
                    "carrier_reference": carrier_ref,
                    "quota": quota_snapshot(sub),
                }
            raise

    sub = increment_labels_used(account_id)
    return 200, {
        "success": True,
        "tracking_number": tracking,
        "label_base64": label_b64,
        "carrier_reference": carrier_ref,
        "quota": quota_snapshot(sub),
    }
