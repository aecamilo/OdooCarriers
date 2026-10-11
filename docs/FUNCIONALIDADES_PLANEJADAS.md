> Alinhado a [PROPOSTA_FUNCIONAL.md](./PROPOSTA_FUNCIONAL.md) (documento mestre).

# Funcionalidades planejadas (por origem)

Lista objetiva do que implantar para competir com conectores DPD já vendidos na Odoo Apps (NSInfosystem, Webkul, BrowseInfo, etc.), usando **Odoo IAP + gateway central** como diferencial.

**Legenda:** **MVP** = primeira entrega útil; **v1** = pacote comercial completo por país; **v2** = reforço competitivo.

---

## Database (persistência no gateway)

| # | Funcionalidade | Prioridade | Notas |
|---|----------------|------------|-------|
| 1 | Cadastro de conexões (empresa Odoo, armazém, país, ambiente stage/live) | MVP | Referência opaca; sem segredos no Odoo |
| 2 | Credenciais DPD criptografadas por conexão | MVP | Rotação e revogação centralizadas |
| 3 | Remessas (ref gateway, ref DPD, tracking, status, picking ref) | MVP | Base para idempotência e painel |
| 4 | Chaves de idempotência e resultado cacheado | MVP | Evita etiqueta/cobrança duplicada |
| 5 | Fila de retentativas (falhas transitórias) | v1 | Backoff; não retentar erro de dados |
| 6 | Exceções (categoria, severidade, estado, mensagem, ação sugerida) | v1 | Alimenta painel Odoo |
| 7 | Eventos de tracking (timestamp, código, texto) | v1 | Webhook e/ou polling |
| 8 | Log de auditoria de chamadas (request/response sanitizados) | v1 | Suporte e disputas |
| 9 | Consumo IAP (operações debitadas, saldo, pacote) | v1 | Créditos / pacote anual |
| 10 | Manifestos / fechamento do dia por conexão e data | v2 | Concorrentes destacam manifest slip |
| 11 | Retenção e política LGPD/GDPR (anonimizar stage) | v1 | Exigência DPD NL/BE em teste |

---

## Gateway (API + adaptadores DPD)

| # | Funcionalidade | Prioridade | Notas |
|---|----------------|------------|-------|
| 1 | Health e versão da API | MVP | `/healthz`, `/api/v1/version` |
| 2 | Autenticação Odoo IAP + validação `database.uuid` | MVP | Sem token manual (transição: Bearer + IAP) |
| 3 | Teste de conexão por país (auth, depot, permissões) | MVP | Onboarding |
| 4 | Listagem de serviços/produtos DPD disponíveis na conta | MVP | Sync para métodos de entrega |
| 5 | Cotação (rate) a partir do modelo normalizado | MVP | SO / checkout |
| 6 | Criar remessa (store order / shipment) | MVP | |
| 7 | Etiqueta (PDF A4/A6, ZPL) | MVP | Concorrência exige multi-formato |
| 8 | Cancelar remessa | v1 | Vraja/Webkul anunciam |
| 9 | Devolução + etiqueta de retorno | v1 | |
| 10 | Múltiplos volumes na mesma remessa | v1 | Várias etiquetas por picking |
| 11 | Parcel shop / pickup point (busca + seleção) | v1 | Diferencial FR/DE nos concorrentes |
| 12 | COD (cash on delivery) | v1 | Onde API nacional permitir |
| 13 | Seguro / valor declarado | v2 | |
| 14 | Coleta (pickup request) | v2 | |
| 15 | Manifesto / export end-of-day | v2 | |
| 16 | Tracking (consulta + ingestão webhook) | v1 | Não só link externo |
| 17 | Documentos internacionais (export/customs) | v2 | FR/DE |
| 18 | Adaptadores isolados: DE, FR, NL, BE, UK | MVP→v1 | NL ≠ BE |
| 19 | Erros traduzidos (código + mensagem + ação) | v1 | Menos suporte manual |
| 20 | Limites de taxa e timeout por operação DPD | v1 | Estabilidade |

---

## Odoo (módulos `addons/`)

| # | Funcionalidade | Prioridade | Notas |
|---|------|------------|-------|
| 1 | Módulo base `odoocarriers_base` (dependência comum) | MVP | |
| 2 | Assistente de onboarding (país → credenciais → teste → serviços) | MVP | Diferencial vs “cole o token” |
| 3 | Cliente HTTP único para o gateway | MVP | `gateway_client` |
| 4 | Integração `delivery.carrier` (get rate, send shipping) | MVP | Fluxo padrão Odoo |
| 5 | Campos em transferência (tracking, ref gateway, etiqueta) | MVP | |
| 6 | Configuração URL do gateway (Settings) | MVP | |
| 7 | Painel de exceções (lista, filtros, severidade, retry) | v1 | Poucos concorrentes fazem bem |
| 8 | Conexões DPD (form/tree por país) | MVP | |
| 9 | Métodos de entrega gerados/sync a partir dos serviços DPD | v1 | |
| 10 | Checkout e-commerce (rate + parcel shop) | v1 | `website_sale` |
| 11 | Produção vs teste (smart button / flag) | MVP | Evita cobrança acidental |
| 12 | Multi-empresa / multi-armazém | v1 | Concorrentes FR destacam |
| 13 | Impressão em lote de etiquetas | v2 | NSInfosystem FR |
| 14 | E-mail ao cliente com tracking (template Odoo) | v2 | Opcional |
| 15 | Regras de frete fixo/regra quando API não cota | v1 | DE Paket-style |
| 16 | Módulos por país (`delivery_dpd_de`, …) para Odoo Apps | v1 | SEO na loja |
| 17 | `delivery_dpd_europe` (metadados / dependências) | MVP | |
| 18 | Integração Odoo IAP (conta automática, compra créditos) | v1 | Modelo comercial |
| 19 | Debug request (modo técnico, link para log gateway) | v2 | Paridade Odoo nativo |
| 20 | Chatter: atualizações de status na entrega | v1 | |

---

## Mapa rápido (quem faz o quê)

```
┌─────────────────────────────────────────────────────────────────┐
│ ODOO          │ cota na SO, valida picking, UI, IAP, exceções   │
├───────────────┼─────────────────────────────────────────────────┤
│ GATEWAY       │ adaptadores DPD, regras, tradução, filas        │
├───────────────┼─────────────────────────────────────────────────┤
│ DATABASE      │ conexões, remessas, idempotência, tracking, IAP │
└─────────────────────────────────────────────────────────────────┘
```

---

## Paridade mínima com o mercado (checklist)

Para não perder vendas na Apps Store, o **v1 por país** deve cobrir pelo menos:

- Credenciais + teste de conexão
- Cotação (ou regra de frete documentada)
- Etiqueta na validação da entrega
- Tracking visível no Odoo
- Cancelamento (se API suportar)
- PDF (A6) e preferencialmente ZPL
- Ambiente de teste

### Acima do mercado (nossa aposta)

- Onboarding sem conta externa + IAP
- Painel de exceções com retry
- Um gateway multipaís (mesma carteira de créditos)
- Idempotência e auditoria central

---

Ver [ROADMAP_IMPLEMENTACAO.md](./ROADMAP_IMPLEMENTACAO.md) para o estado actual no repositório.
