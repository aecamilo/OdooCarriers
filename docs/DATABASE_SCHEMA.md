# MySQL — OdooCarriers Hub Gateway

Base: **`odoocarriers`** (utilizador `saas` no ambiente de testes Hetzner).

DDL: [`sql/odoocarriers_schema.sql`](sql/odoocarriers_schema.sql)  
Bootstrap BD: [`sql/setup_odoocarriers_saas.sql`](sql/setup_odoocarriers_saas.sql)

Planos (RPM, franquia): [`config/plan_catalog.json`](config/plan_catalog.json) — **não** há tabela SQL de planos.

## Tabelas

| Tabela | Função |
|--------|--------|
| `accounts` | Tenant; `status`; `odoo_database_uuid` (único); hash opcional de `iap_account_token` |
| `api_token_hashes` | Hash SHA-256(token + pepper); lookup Bearer Odoo |
| `subscriptions` | Plano, estado, `usage_yyyymm`, `labels_used` |
| `hmac_nonces` | Anti-replay HMAC (TTL) |
| `rate_limit_windows` | RPM/burst por janela UTC |
| `shipment_logs` | Auditoria quota (sem moradas/PDF) |
| `iap_transactions` | Transacções IAP idempotentes |
| `iap_credit_ledger` | Movimentos de crédito internos |
| `connections` | Conexão DPD por conta (país, ambiente, refs Odoo) |
| `connection_secrets` | Credenciais DPD cifradas (Fernet + `GATEWAY_SECRETS_KEY`) |

## Segurança

- Token API: nunca em claro na BD; apenas `BINARY(32)` hash com `SAAS_KEY_PEPPER`.
- Credenciais DPD **no gateway** (`connection_secrets`); Odoo não persiste segredos (PROPOSTA §1).
- Migration: [`sql/migrations/002_connections_and_uuid.sql`](sql/migrations/002_connections_and_uuid.sql).
