# Odoo Apps Store e IAP — como a compra chega ao editor

Documento técnico para o projeto **OdooCarriers**. Fonte de produto: `PROPOSTA_FUNCIONAL.md`.

Referências oficiais (consultadas em 2026-03-11):

- [Odoo Apps FAQ](https://apps.odoo.com/apps/faq)
- [Vendor Guidelines](https://apps.odoo.com/apps/vendor-guidelines)
- [In-App Purchase (developer API)](https://www.odoo.com/documentation/16.0/developer/api/iap.html)

---

## Resumo executivo

| Expectativa comum | Realidade na plataforma Odoo |
|-------------------|------------------------------|
| A Store envia **webhook HTTP** ao editor em cada compra ou download | **Não documentado** para editores. Vendas no **painel de vendas** Apps; pagamento via PO/fatura. |
| O ZIP inclui automaticamente um **token SaaS** gerado pela Odoo | **Não**. Email com links **temporários** (~1 h); depois download na **página de encomendas** (conta Odoo.com). |
| Limites de uso só pela venda do módulo | Venda do módulo (`price` no manifest) é **licença do addon**. Consumo recorrente: **IAP (créditos)**. |

**Implicação:** provisioning MySQL + token API + quotas → **IAP + activação no módulo**, não webhook genérico da Store em cada download.

---

## 1. Venda do módulo na Odoo Apps Store

### 1.1 O que o comprador recebe

1. Compra com conta **Odoo.com**.
2. Email com links temporários de download (~**1 hora**).
3. Depois: download em [My Orders](https://apps.odoo.com/my/orders) ou na página do módulo.
4. Instalação: ZIP → `addons` → actualizar apps → instalar.

### 1.2 O que o editor recebe

- Dashboard de vendas Apps (PO, 30% comissão Odoo).
- **Sem** webhook documentado por compra/download.
- Suporte via Orders → Support na Store.

### 1.3 Publicação

- `__manifest__.py`: `price`, `currency`, `license` (ex. OPL-1).
- `static/description/index.html`, opcional `doc/index.rst`.
- Repo Git SSH na Store.

**Odoo Online:** módulos third-party com Python em geral **não** instaláveis; **Odoo.sh** / on-premise.

---

## 2. In-App Purchase (IAP)

Serviços contínuos por **créditos** (ex.: etiquetas).

| Actor | Função |
|-------|--------|
| iap.odoo.com | Carteira, authorize/capture |
| Módulo Odoo | `depends: iap`; `env['iap.account'].get('service_name').account_token` |
| Gateway Python | Serviço registado em IAP; executa etiqueta |

Registo: [iap.odoo.com](https://iap.odoo.com) / sandbox. Comissão IAP: **25%** Odoo.

### Fluxo (1 etiqueta ≈ 1 crédito)

1. **Authorize** — reserva créditos (`/iap/1/authorize`).
2. Executar serviço no gateway.
3. **Capture** ou **Cancel** (`/iap/1/capture`).

Helper: `iap_charge(env, service_key, account_token, credit, ...)`.

### MySQL (backend)

1. Wizard/1.ª utilização: módulo envia `account_token` (+ metadados) → `POST /api/v1/accounts/provision` (proposto).
2. Gateway cria tenant MySQL, devolve **token API** (mostrar uma vez; hash em BD).
3. Etiquetas: **HMAC** existente (`shipping_hub_client.py`) + quota MySQL + débito IAP alinhado.

---

## 3. Evitar como desenho base

- Webhook Store por download com token automático (não documentado).
- Legado hubCarrier / portal PHP / Stripe para provisioning Store.

---

## 4. Opções complementares

| Opção | Notas |
|-------|--------|
| **IAP (recomendado)** | Quotas e compra de créditos oficiais |
| Export manual dashboard Apps | Sem automação |
| Odoo interno do editor | Apps Management (terceiros); não API Store oficial |
| Activación pós-instalação | Wizard com account_token IAP |

---

## 5. Módulo `shipping_hub_connector`

- `depends`: incluir `iap`.
- Etiqueta: tratar `InsufficientCreditError`; link para comprar créditos.
- Testes: IAP sandbox + simulador gateway.

---

## 6. Gateway Python

| Endpoint | Função |
|----------|--------|
| `POST /api/v1/shipments/labels` | HMAC + Bearer (actual) |
| Serviço IAP registado | Chamado via iap.odoo.com ao consumir créditos |
| `POST /api/v1/accounts/provision` | LigAR account_token → token API |

---

## 7. Validar com Odoo se necessário

- API editor para vendas automatizadas (não na FAQ pública).
- IAP + módulo OPL pago na mesma app.
- Odoo.sh: outbound HTTPS ao gateway.

---

## 8. Registo IAP sandbox (OdooCarriers)

1. Criar serviço em [iap.odoo.com](https://iap.odoo.com) (sandbox) com nome **`odoocarriers_shipping_labels`** (ou alinhar `IAP_SERVICE_NAME` / settings Odoo).
2. URL pública do serviço: `{APP_PUBLIC_URL}/iap/1/odoocarriers_shipping_labels` (ex.: `https://stip.pt/hub-test/iap/1/odoocarriers_shipping_labels`).
3. Definir **`IAP_SERVICE_KEY`** no `.env` do gateway (mesmo valor no header `Authorization: Bearer …` que o portal IAP envia).
4. Provision: `POST /api/v1/accounts/provision` com header `X-OdooCarriers-Provision-Key` (= `IAP_SERVICE_KEY`) ou `APP_DEBUG=true` em dev.
5. Odoo: wizard **Provision API token (IAP)** ou `scripts/seed-dev-account.sh`; activar **Skip IAP charge** só para testes locais sem iap.odoo.com.

## Histórico

| Data | Alteração |
|------|-----------|
| 2026-03-11 | Documento inicial; IAP em vez de webhook Store |
