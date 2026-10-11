# -*- coding: utf-8 -*-

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class ShippingHubProvisionWizard(models.TransientModel):
    _name = 'shipping_hub.provision.wizard'
    _description = 'Activate Shipping Hub API token via IAP'

    iap_account_token = fields.Char(string='IAP account token', required=True)
    contact_email = fields.Char(string='Contact email')
    api_token = fields.Char(string='API token (shown once)', readonly=True)

    def action_provision(self):
        self.ensure_one()
        settings = self.env['res.config.settings']
        base_url = settings._shipping_hub_resolve_base_url()
        icp = self.env['ir.config_parameter'].sudo()
        provision_key = icp.get_param('shipping_hub_connector.provision_key', '')

        token = self.iap_account_token.strip()
        if not token:
            raise UserError(_('IAP account token is required.'))

        url = f"{base_url.rstrip('/')}/api/v1/accounts/provision"
        headers = {'Content-Type': 'application/json'}
        if provision_key:
            headers['X-OdooCarriers-Provision-Key'] = provision_key
        payload = {
            'iap_account_token': token,
            'contact_email': self.contact_email or None,
            'plan_code': 'free',
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            raise UserError(_('Could not reach the gateway for provisioning.')) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise UserError(_('Invalid response from gateway provisioning.')) from exc

        if not response.ok or not body.get('success'):
            detail = body.get('error_detail') or body.get('error_code') or response.reason
            raise UserError(_('Provisioning failed: %s') % detail)

        api_token = body.get('api_token')
        if not api_token:
            raise UserError(_('Gateway did not return an API token.'))

        icp.set_param('shipping_hub_connector.api_token', api_token)
        self.api_token = api_token
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
