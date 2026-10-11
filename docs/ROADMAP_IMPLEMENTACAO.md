# Roadmap de implementação vs código

**Mestre:** [PROPOSTA_FUNCIONAL.md](./PROPOSTA_FUNCIONAL.md) (secção 11).  
**Detalhe funcional:** [FUNCIONALIDADES_PLANEJADAS.md](./FUNCIONALIDADES_PLANEJADAS.md).

## Secção 11 — ordem PROPOSTA

| # | Marco PROPOSTA | Estado | Evidência no repo |
|---|----------------|--------|-------------------|
| 1 | `odoocarriers_base` + IAP | 🟡 Parcial | `shipping_hub_connector` + `iap` charge; falta módulo base DPD |
| 2 | Gateway mínimo + health | 🟢 | `hub-gateway` `/healthz`, `/api/v1/version` |
| 3 | Adaptador país 1 (DE/FR) | 🔴 | Simulador genérico; sem adapter DPD |
| 4 | Onboarding + 1ª etiqueta | 🟡 | Wizard provision; falta fluxo país→credenciais DPD |
| 5 | Exceções + tracking | 🔴 | Tabelas/serviços v1 |
| 6 | NL, BE, UK | 🔴 | — |
| 7 | Odoo Apps listagens | 🔴 | — |

Legenda: 🟢 feito · 🟡 parcial · 🔴 pendente

## MVP técnico (FUNCIONALIDADES — Database/Gateway/Odoo)

| Item | Estado |
|------|--------|
| IAP JSON-RPC no gateway | 🟢 |
| Header `X-Odoo-Database-Uuid` | 🟢 |
| Tabelas `connections` + `connection_secrets` | 🟢 (migration SQL) |
| `POST /api/v1/dpd/connections/test` (stub) | 🟢 |
| Token API manual (ponte) | 🟡 — remover quando IAP-only |
| `addons/odoocarriers_base` | 🔴 |

## Próximo sprint sugerido

1. `odoocarriers_base` mínimo (`gateway_client`, IAP-only settings).  
2. Adaptador DPD **DE** ou **NL** (sandbox).  
3. Onboarding PROPOSTA §6 (credenciais → teste gateway).
