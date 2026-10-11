# -*- coding: utf-8 -*-

import base64
import logging
import re
import uuid

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError

from .shipping_hub_client import ShippingHubClient, humanize_hub_error


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipping_hub_label_id = fields.Char(
        string='Hub label id',
        copy=False,
        readonly=True,
        help='Idempotency key / carrier reference for the SaaS shipment log.',
    )
    shipping_hub_last_error = fields.Text(
        string='Last Hub error',
        copy=False,
        readonly=True,
    )
    shipping_hub_number_of_packages = fields.Integer(
        string='Number of packages',
        default=1,
        copy=False,
        help='Number of physical parcels (colli) sent to the Hub for label generation.',
    )
    shipping_hub_show_generate = fields.Boolean(
        compute='_compute_shipping_hub_ui_flags',
    )
    shipping_hub_show_cancel = fields.Boolean(
        compute='_compute_shipping_hub_ui_flags',
    )
    shipping_hub_show_tracking = fields.Boolean(
        compute='_compute_shipping_hub_ui_flags',
    )

    @api.depends(
        'state',
        'carrier_tracking_ref',
        'carrier_id',
        'carrier_id.delivery_type',
        'picking_type_id.code',
    )
    def _compute_shipping_hub_ui_flags(self):
        for picking in self:
            hub = (
                picking.picking_type_id.code == 'outgoing'
                and picking.carrier_id
                and picking.carrier_id.delivery_type == 'shipping_hub'
            )
            picking.shipping_hub_show_generate = bool(
                hub
                and picking.state in ('assigned', 'done')
                and not picking.carrier_tracking_ref
            )
            picking.shipping_hub_show_cancel = bool(hub and picking.carrier_tracking_ref)
            picking.shipping_hub_show_tracking = bool(
                hub
                and picking.carrier_tracking_ref
                and picking.carrier_id._shipping_hub_tracking_url(picking.carrier_tracking_ref)
            )

    def _shipping_hub_is_outgoing(self):
        self.ensure_one()
        code = self.picking_type_id.code
        return code == 'outgoing'

    def _shipping_hub_get_warehouse(self):
        self.ensure_one()
        warehouse = self.picking_type_id.warehouse_id or self.location_id.warehouse_id
        return warehouse

    def _shipping_hub_get_shipper_partner(self):
        self.ensure_one()
        warehouse = self._shipping_hub_get_warehouse()
        if not warehouse or not warehouse.partner_id:
            raise UserError(
                _('Warehouse partner is missing for %(picking)s. Complete the warehouse address.')
                % {'picking': self.name}
            )
        return warehouse.partner_id

    @staticmethod
    def _shipping_hub_partner_to_party(partner, require_company_name=False):
        country_code = partner.country_id.code if partner.country_id else False
        if not country_code:
            raise UserError(
                _('Partner %(name)s has no country set.') % {'name': partner.display_name}
            )
        street = partner.street or ''
        if not street:
            raise UserError(
                _('Partner %(name)s has no street address.') % {'name': partner.display_name}
            )
        party = {
            'country_code': country_code,
            'postal_code': partner.zip or '',
            'city': partner.city or '',
            'street': street,
            'contact_phone': partner.phone or partner.mobile or '',
        }
        if partner.email:
            party['contact_email'] = partner.email
        if partner.street2:
            party['street2'] = partner.street2
        if require_company_name:
            party['company_name'] = partner.name or partner.parent_id.name or 'Shipper'
        else:
            party['name'] = partner.name or partner.parent_id.name or 'Recipient'
            if partner.parent_id and partner.parent_id.is_company:
                party['company_name'] = partner.parent_id.name
        phone = (party.get('contact_phone') or '').replace(' ', '').strip()
        if len(phone) < 6:
            raise UserError(
                _('Partner %(name)s needs a phone number (required by carriers).')
                % {'name': partner.display_name}
            )
        if not require_company_name:
            email = (party.get('contact_email') or '').strip()
            if not email or '@' not in email:
                raise UserError(
                    _('Delivery contact %(name)s needs an email address (required by carriers).')
                    % {'name': partner.display_name}
                )
        if not party.get('postal_code') or not party.get('city'):
            raise UserError(
                _('Partner %(name)s needs postal code and city.') % {'name': partner.display_name}
            )
        return party

    def _shipping_hub_can_generate_label(self):
        self.ensure_one()
        if not self._shipping_hub_is_outgoing():
            return False
        if self.state not in ('assigned', 'done'):
            return False
        if not self.carrier_id or self.carrier_id.delivery_type != 'shipping_hub':
            return False
        if self.carrier_tracking_ref:
            return False
        return True

    def _shipping_hub_parcel_count(self):
        self.ensure_one()
        if self.shipping_hub_number_of_packages and self.shipping_hub_number_of_packages > 0:
            return int(self.shipping_hub_number_of_packages)
        if 'package_ids' in self._fields:
            package_count = len(self.package_ids)
            if package_count:
                return package_count
        return 1

    def _shipping_hub_total_weight_kg(self):
        self.ensure_one()
        if 'shipping_weight' in self._fields:
            weight = self.shipping_weight
            if weight and weight > 0:
                return weight
        if 'weight' in self._fields:
            weight = self.weight
            if weight and weight > 0:
                return weight
        total = sum(
            self.move_ids.mapped(lambda m: (m.product_id.weight or 0.0) * m.product_qty)
        )
        return total or 0.0

    def _shipping_hub_build_payload(self, idempotency_key):
        self.ensure_one()
        carrier = self.carrier_id
        shipper = self._shipping_hub_get_shipper_partner()
        recipient = self.partner_id
        if not recipient:
            raise UserError(_('Delivery address (customer) is missing on %(picking)s.') % {
                'picking': self.name,
            })

        packages = self._shipping_hub_parcel_count()
        total_weight = self._shipping_hub_total_weight_kg()
        if not total_weight or total_weight <= 0:
            raise UserError(
                _('Shipping weight must be greater than zero on %(picking)s.')
                % {'picking': self.name}
            )
        weight_each = total_weight / packages

        parcels = [{'weight_kg': round(weight_each, 3)} for _ in range(packages)]

        return {
            'schema_version': '1.0',
            'operation': 'create_shipment',
            'idempotency_key': idempotency_key,
            'carrier_code': carrier.shipping_hub_carrier_code,
            'service_level': carrier.shipping_hub_service_level or 'standard',
            'reference': self.name,
            'shipper': self._shipping_hub_partner_to_party(shipper, require_company_name=True),
            'recipient': self._shipping_hub_partner_to_party(recipient, require_company_name=False),
            'parcels': parcels,
        }

    def _shipping_hub_settings(self):
        return self.env['res.config.settings']

    def _shipping_hub_get_client(self):
        settings = self._shipping_hub_settings()
        base_url = settings._shipping_hub_resolve_base_url()
        token = settings._shipping_hub_get_api_token()
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid') or ''
        return ShippingHubClient(base_url, token, database_uuid=db_uuid)

    def _shipping_hub_raise_label_error(self, result):
        self.ensure_one()
        carrier_name = self.carrier_id.name or _('Carrier')
        reason = humanize_hub_error(result)
        self.shipping_hub_last_error = reason
        raise UserError(
            _('Label issue failed (%(carrier)s)\n'
              'Could not generate a label for order %(ref)s.\n'
              'Reason from the Hub:\n'
              '%(reason)s')
            % {
                'carrier': carrier_name,
                'ref': self.name,
                'reason': reason,
            }
        )

    def _shipping_hub_label_filename(self, carrier_code):
        safe_name = re.sub(r'[^\w\-]+', '_', self.name or 'picking')
        code = re.sub(r'[^\w\-]+', '_', (carrier_code or 'label').lower())
        return f'label_{code}_{safe_name}.pdf'

    def _shipping_hub_attach_label(self, label_b64, carrier_code, quota=None, force_attach=None):
        self.ensure_one()
        attach_enabled = force_attach
        if attach_enabled is None:
            attach_enabled = self._shipping_hub_settings()._shipping_hub_auto_attach_enabled()
        if not attach_enabled or not label_b64:
            return

        pdf_bytes = base64.b64decode(label_b64)
        filename = self._shipping_hub_label_filename(carrier_code)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_bytes),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        body = _('Shipping label generated via Shipping Hub.')
        if quota:
            used = quota.get('used')
            limit = quota.get('limit')
            plan = quota.get('plan')
            if used is not None:
                if limit:
                    body += '<br/>' + _('Quota: %(used)s / %(limit)s (%(plan)s)') % {
                        'used': used,
                        'limit': limit,
                        'plan': plan or '',
                    }
                else:
                    body += '<br/>' + _('Quota used: %(used)s (%(plan)s)') % {
                        'used': used,
                        'plan': plan or '',
                    }
        self.message_post(body=body, attachment_ids=[attachment.id])

    @api.model
    def _shipping_hub_parse_label_response(self, result):
        """Extract tracking, PDF and carrier reference from Gateway JSON (tolerant)."""
        if not isinstance(result, dict):
            return '', '', '', None

        payload = result
        nested = result.get('data')
        if isinstance(nested, dict):
            payload = {**nested, **{k: v for k, v in result.items() if k != 'data'}}

        label_block = payload.get('label')
        label_dict = label_block if isinstance(label_block, dict) else {}

        def _str(value):
            if value is None or value is False:
                return ''
            if isinstance(value, (int, float)):
                return str(value)
            return str(value).strip()

        tracking = _str(
            payload.get('tracking_number')
            or payload.get('trackingNumber')
            or payload.get('barcode')
            or payload.get('shipmentTrackingNumber')
            or label_dict.get('tracking_number')
        )
        label_b64 = (
            payload.get('label_base64')
            or payload.get('labelBase64')
            or label_dict.get('content_base64')
            or label_dict.get('content')
            or (label_block if isinstance(label_block, str) else '')
            or ''
        )
        if isinstance(label_b64, str):
            label_b64 = label_b64.strip()
        else:
            label_b64 = ''

        carrier_ref = _str(
            payload.get('carrier_reference')
            or payload.get('carrierReference')
            or payload.get('shipmentId')
            or payload.get('dispatchConfirmationNumber')
        )
        if not tracking and carrier_ref:
            tracking = carrier_ref

        quota = payload.get('quota') or result.get('quota')
        return tracking, label_b64, carrier_ref, quota

    def _shipping_hub_apply_label_response(self, result, idempotency_key, force_attach=None):
        self.ensure_one()
        tracking, label_b64, carrier_ref, quota = self._shipping_hub_parse_label_response(
            result
        )
        label_id = carrier_ref or idempotency_key

        if not tracking:
            _logger.warning(
                'Shipping Hub label for %s: no tracking in gateway response keys=%s',
                self.name,
                sorted(k for k in result.keys() if k != 'label_base64') if isinstance(result, dict) else [],
            )

        self.write({
            'carrier_tracking_ref': tracking or False,
            'shipping_hub_label_id': label_id,
            'shipping_hub_last_error': False,
        })
        carrier_code = self.carrier_id.shipping_hub_carrier_code
        self._shipping_hub_attach_label(
            label_b64,
            carrier_code,
            quota=quota,
            force_attach=force_attach,
        )
        if label_b64 and not tracking:
            self.message_post(
                body=_(
                    'Label PDF received from Shipping Hub, but no tracking number was returned. '
                    'Check the carrier portal or gateway logs.'
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )


    def _shipping_hub_iap_charge(self):
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param('shipping_hub_connector.skip_iap_charge', 'False') == 'True':
            return
        service_name = icp.get_param(
            'shipping_hub_connector.iap_service_name',
            'odoocarriers_shipping_labels',
        )
        account = self.env['iap.account'].get(service_name)
        if not account or not account.account_token:
            raise UserError(
                _('No IAP account configured for %(service)s. Buy credits or enable '
                  '"Skip IAP charge" for sandbox tests.')
                % {'service': service_name}
            )
        from odoo.addons.iap.tools import iap_tools
        try:
            iap_tools.iap_charge(
                self.env,
                service_name,
                account.account_token,
                1,
                description=self.name or 'Shipping Hub label',
            )
        except iap_tools.InsufficientCreditError as exc:
            raise UserError(
                _('Insufficient IAP credits for a label. Purchase credits in Odoo IAP.')
            ) from exc

    def _shipping_hub_generate_label(self, force_attach=None):
        self.ensure_one()
        if not self._shipping_hub_can_generate_label():
            raise UserError(
                _('This delivery is not eligible for a Shipping Hub label.')
            )

        idempotency_key = self.shipping_hub_label_id or str(uuid.uuid4())
        payload = self._shipping_hub_build_payload(idempotency_key)
        self._shipping_hub_iap_charge()
        client = self._shipping_hub_get_client()
        result = client.create_label(payload)
        if not result.get('success'):
            self._shipping_hub_raise_label_error(result)
        self._shipping_hub_apply_label_response(result, idempotency_key, force_attach=force_attach)
        return True

    def action_shipping_hub_generate_label(self):
        for picking in self:
            picking._shipping_hub_generate_label(force_attach=True)
        return True

    def action_shipping_hub_cancel_label(self):
        for picking in self:
            if not picking.carrier_tracking_ref and not picking.shipping_hub_label_id:
                continue
            user_name = self.env.user.name
            picking.write({
                'carrier_tracking_ref': False,
                'shipping_hub_label_id': False,
                'shipping_hub_last_error': False,
            })
            picking.message_post(
                body=_(
                    'Label and tracking code removed from Odoo by %(user)s. '
                    'Cancellation with the carrier must be handled manually.'
                ) % {'user': user_name},
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_open_shipping_hub_tracking(self):
        self.ensure_one()
        if not self.carrier_tracking_ref or not self.carrier_id:
            raise UserError(_('No tracking number available.'))
        url = self.carrier_id._shipping_hub_tracking_url(self.carrier_tracking_ref)
        if not url:
            raise UserError(_('No public tracking URL configured for this carrier code.'))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def button_validate(self):
        res = super().button_validate()
        # Do not auto-generate when validation opens a wizard (backorder, immediate transfer, etc.).
        if res is not True and isinstance(res, dict):
            return res
        if not self._shipping_hub_settings()._shipping_hub_auto_generate_enabled():
            return res
        for picking in self:
            if picking._shipping_hub_can_generate_label():
                picking._shipping_hub_generate_label()
        return res

    def action_shipping_hub_batch_generate_labels(self):
        eligible = self.filtered(lambda p: p._shipping_hub_can_generate_label())
        skipped = self - eligible
        pdf_parts = []
        errors = []

        for picking in eligible:
            try:
                idempotency_key = picking.shipping_hub_label_id or str(uuid.uuid4())
                payload = picking._shipping_hub_build_payload(idempotency_key)
                result = picking._shipping_hub_get_client().create_label(payload)
                if not result.get('success'):
                    msg = humanize_hub_error(result)
                    picking.shipping_hub_last_error = msg
                    errors.append('%s: %s' % (picking.name, msg))
                    continue
                picking._shipping_hub_apply_label_response(result, idempotency_key, force_attach=True)
                _tracking, label_b64, _ref, _quota = picking._shipping_hub_parse_label_response(
                    result
                )
                if label_b64:
                    pdf_parts.append(base64.b64decode(label_b64))
            except UserError as exc:
                errors.append('%s: %s' % (picking.name, exc.args[0]))

        for picking in skipped:
            errors.append(
                '%s: %s' % (picking.name, _('Not eligible for batch label generation.'))
            )

        wizard = self.env['shipping.hub.batch.labels.wizard'].create({
            'errors_summary': '\n'.join(errors) if errors else False,
        })
        if pdf_parts:
            wizard.set_merged_pdf(pdf_parts)

        return {
            'name': _('Batch Shipping Hub labels'),
            'type': 'ir.actions.act_window',
            'res_model': 'shipping.hub.batch.labels.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': wizard.id,
        }
