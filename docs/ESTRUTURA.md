# Estrutura do repositório

Alvo definido em [PROPOSTA_FUNCIONAL.md](./PROPOSTA_FUNCIONAL.md) §3. **Não** renomear pastas em massa até os módulos `addons/` existirem.

## Mapa actual → alvo

| Alvo | Caminho actual | Acção |
|------|----------------|-------|
| `docs/PROPOSTA_FUNCIONAL.md` | ✅ `docs/PROPOSTA_FUNCIONAL.md` | Manter como mestre |
| `docs/FUNCIONALIDADES_PLANEJADAS.md` | ✅ | Backlog detalhado |
| `carrier_gateway/` | `hub-gateway/` | Documentar como interim; deploy/scripts já apontam aqui |
| `addons/odoocarriers_base` | `shipping_hub_connector/` | Ponte; extrair `gateway_client` comum depois |
| `addons/delivery_dpd_*` | — | Criar na fase MVP país |
| `deploy/` | `deploy/` | ✅ |
| `scripts/` | `scripts/` | ✅ |

## Árvore simplificada (hoje)

```
OdooCarriers/
├── docs/
├── hub-gateway/              # interim carrier_gateway
├── shipping_hub_connector/     # interim até odoocarriers_base
├── deploy/
└── scripts/
```

## Migração de nomes (futuro)

1. Introduzir `addons/` com `odoocarriers_base` (dependência de `shipping_hub_connector` ou substituição gradual).  
2. Quando estável, alias documental `hub-gateway` → `carrier_gateway` (opcional rename + systemd paths).  
3. Retirar token manual e URLs HubCarrier do código Odoo (PROPOSTA §12).
