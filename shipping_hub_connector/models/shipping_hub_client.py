# -*- coding: utf-8 -*-
"""HTTP client for the Shipping Hub Gateway (HMAC-SHA256 + Bearer)."""

import hashlib
import hmac
import json
import logging
import time
import uuid

import requests

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LABELS_PATH = '/api/v1/shipments/labels'
SCHEMA_VERSION = '1.0'
REQUEST_TIMEOUT_SEC = 30


def _error_messages():
    return {
        'invalid_payload': _(
            'Incomplete shipment data (address, postal code, weight, or carrier settings).'
        ),
        'monthly_quota_exceeded': _('Monthly label quota has been reached.'),
        'quota_exceeded': _('Monthly label quota has been reached.'),
        'rate_limit_exceeded': _(
            'Too many requests; please wait about one minute and try again.'
        ),
        'carrier_credentials_missing': _(
            'Carrier API credentials are missing in the Shipping Hub portal.'
        ),
        'carrier_misconfigured': _(
            'Carrier API credentials are invalid. Update account and API key in the Shipping Hub portal.'
        ),
        'subscription_inactive': _('Your Shipping Hub subscription is not active.'),
        'invalid_token': _('Invalid API token. Update it in Inventory settings.'),
        'invalid_database_uuid': _(
            'Database identity rejected by the gateway. Contact support if this persists.'
        ),
        'invalid_signature': _('Request signature rejected. Check the API token.'),
        'timestamp_out_of_range': _('Request timestamp out of range. Sync server time.'),
        'nonce_reused': _('Duplicate request nonce. Try again.'),
        'carrier_error': _('The carrier rejected the shipment request.'),
    }


class ShippingHubClient:
    """Signed REST client for label creation."""

    def __init__(self, base_url, api_token, database_uuid=None):
        self.base_url = (base_url or '').rstrip('/')
        self.api_token = api_token or ''
        self.database_uuid = (database_uuid or '').strip()

    def _sign(self, method, path, body_bytes, timestamp, nonce):
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        canonical = f'{method}\n{path}\n\n{timestamp}\n{nonce}\n{body_hash}\n'
        digest = hmac.new(
            self.api_token.encode('utf-8'),
            canonical.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return f'sha256={digest}'

    def _headers(self, body_bytes, timestamp, nonce, signature):
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json; charset=utf-8',
            'X-SC-Timestamp': timestamp,
            'X-SC-Nonce': nonce,
            'X-SC-Signature': signature,
            'X-SC-Schema-Version': SCHEMA_VERSION,
        }
        if self.database_uuid:
            headers['X-Odoo-Database-Uuid'] = self.database_uuid
        return headers

    def _request(self, method, path, body_dict=None):
        if not self.base_url:
            raise UserError(_('Shipping Hub gateway URL is not configured.'))
        if not self.api_token or len(self.api_token) < 16:
            raise UserError(_('Shipping Hub API token is missing or too short.'))

        url = f'{self.base_url}{path}'
        if body_dict is not None:
            body_bytes = json.dumps(
                body_dict, separators=(',', ':'), ensure_ascii=False
            ).encode('utf-8')
        else:
            body_bytes = b''

        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())
        signature = self._sign(method, path, body_bytes, timestamp, nonce)
        headers = self._headers(body_bytes, timestamp, nonce, signature)

        try:
            response = requests.request(
                method,
                url,
                data=body_bytes if body_dict is not None else None,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SEC,
            )
        except requests.exceptions.Timeout as exc:
            raise UserError(_('Shipping Hub gateway timed out. Try again later.')) from exc
        except requests.exceptions.RequestException as exc:
            _logger.warning('Shipping Hub network error: %s', exc)
            raise UserError(
                _('Could not reach the Shipping Hub gateway. Check URL and network.')
            ) from exc

        return self._parse_response(response)

    def _parse_response(self, response):
        try:
            payload = response.json() if response.content else {}
        except ValueError:
            payload = {}

        if response.ok and payload.get('success') is True:
            return payload

        error_code = payload.get('error_code') or 'internal_error'
        detail = (payload.get('error_detail') or '').strip()
        messages = _error_messages()
        generic = messages.get(error_code)
        if detail:
            message = detail
            if generic and generic not in detail:
                message = '%s\n%s' % (detail, generic)
        else:
            message = generic or error_code
        return {
            'success': False,
            'http_status': response.status_code,
            'error_code': error_code,
            'error_message': message,
        }

    def create_label(self, body_dict):
        return self._request('POST', LABELS_PATH, body_dict)

    def test_connection(self):
        health_url = f'{self.base_url}/healthz'
        try:
            health = requests.get(health_url, timeout=10)
            health.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise UserError(
                _('Gateway health check failed (%(url)s).') % {'url': health_url}
            ) from exc

        result = self._request('POST', LABELS_PATH, {})
        if result.get('success'):
            raise UserError(_('Unexpected success on connection test.'))
        if result.get('http_status') == 401:
            raise UserError(_('API token rejected by the gateway (401).'))
        if result.get('error_code') == 'invalid_payload':
            return True
        raise UserError(
            _('Connection test failed: %(msg)s')
            % {'msg': result.get('error_message', result.get('error_code'))}
        )


def humanize_hub_error(result):
    if not result or result.get('success'):
        return ''
    return result.get('error_message') or result.get('error_code') or _('Unknown error')
