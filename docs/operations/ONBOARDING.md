# Onboarding DPD (Odoo)

Fluxo: [PROPOSTA_FUNCIONAL.md](../PROPOSTA_FUNCIONAL.md) §6.

1. Instalar módulo (`delivery_dpd_*` ou ponte `shipping_hub_connector`).  
2. Conta **IAP** automática (`iap.account`).  
3. País / armazém / ambiente stage|live.  
4. Credenciais DPD → **gateway** (nunca persistir segredos no Odoo).  
5. `POST /api/v1/dpd/connections/test` no gateway.  
6. Sync serviços → métodos de entrega Odoo.  
7. Remessa de teste + etiqueta → produção.
