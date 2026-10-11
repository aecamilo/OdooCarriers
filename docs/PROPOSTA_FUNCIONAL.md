# Proposta funcional — OdooCarriers

Documento **mestre** de diretrizes do projeto. Qualquer implementação deve estar alinhada a este ficheiro.

Versão: 1.0 · 2026-10-11

---

## 1. Visão

Integração **DPD/Geopost multipaís** para Odoo (Community e Enterprise, Odoo.sh e on-premise), **sem** portal SaaS externo, **sem** token manual (meta comercial) e **sem** dependência de Sendcloud.

| Princípio | Decisão |
|-----------|---------|
| Produto | Conectores Odoo + **carrier gateway** central |
| Cobrança | **Odoo IAP** (créditos / pacotes anuais) |
| Credenciais DPD | Contrato do cliente; armazenadas **no gateway** |
| Identidade Odoo | `iap.account` automático |
| Foco v1 | 5 APIs: **DE, FR, NL, BE, UK** |

### 1.1 Funcionalidades a implantar (por origem)

Relação completa (Database → Gateway → Odoo), prioridades MVP/v1/v2 e checklist de paridade: **[FUNCIONALIDADES_PLANEJADAS.md](./FUNCIONALIDADES_PLANEJADAS.md)**.

| Origem | Exemplos |
|--------|----------|
| Database | Conexões, credenciais cifradas, remessas, idempotência, filas, exceções, tracking, consumo IAP |
| Gateway | IAP auth, teste DPD, cotação, remessa, etiqueta PDF/ZPL, cancelamento, adaptadores DE/FR/NL/BE/UK |
| Odoo | `delivery.carrier`, onboarding, painel de exceções, e-commerce, multi-armazém, módulos por país, IAP |

---

## 2. Arquitetura (visão geral)

```mermaid
flowchart TB
    subgraph odoo [Odoo_addons]
        BASE[odoocarriers_base]
        EU[delivery_dpd_europe]
        DE[delivery_dpd_de]
        FR[delivery_dpd_fr]
        NL[delivery_dpd_nl]
        BE[delivery_dpd_be]
        UK[delivery_dpd_uk]
        BASE --> EU
        EU --> DE
        EU --> FR
        EU --> NL
        EU --> BE
        EU --> UK
    end

    subgraph gateway [carrier_gateway]
        API[API_HTTP_v1]
        IAP[IAP_validate]
        DOM[domain_normalizado]
        SVC[services_fila_idempotencia]
        ADP[adapters_DPD]
        API --> IAP --> SVC --> DOM --> ADP
    end

    subgraph dpd [Operacoes_DPD]
        DPDDE[DPD_Alemanha]
        DPDFR[DPD_Franca]
        DPDNL[DPD_NL]
        DPDBE[DPD_Belux]
        DPDUK[DPD_UK]
    end

    odoo -->|HTTPS_IAP_DB_UUID| API
    ADP --> DPDDE
    ADP --> DPDFR
    ADP --> DPDNL
    ADP --> DPDBE
    ADP --> DPDUK
```

```
┌─────────────┐     Bearer IAP + DB UUID      ┌──────────────────┐
│   Odoo      │ ────────────────────────────► │ Carrier Gateway  │
│  (plugin)   │ ◄──────────────────────────── │  (Python/FastAPI)│
└─────────────┘     JSON normalizado          └────────┬─────────┘
                                                       │
                       ┌───────────────────────────────┼───────────────────────────────┐
                       ▼               ▼               ▼               ▼               ▼
                     DE API          FR API          NL API          BE API          UK API
```

**Estado actual do repo:** o gateway vive em [`hub-gateway/`](../hub-gateway/) (interim `carrier_gateway`); o módulo ponte é [`shipping_hub_connector/`](../shipping_hub_connector/). Ver [ARCHITECTURE.md](./ARCHITECTURE.md) e [ESTRUTURA.md](./ESTRUTURA.md).

---

## 3. Estrutura de pastas do repositório (alvo)

```
OdooCarriers/
├── docs/
│   ├── PROPOSTA_FUNCIONAL.md      ← este documento
│   ├── FUNCIONALIDADES_PLANEJADAS.md
│   ├── ARCHITECTURE.md
│   ├── ESTRUTURA.md
│   └── operations/
│       ├── ONBOARDING.md
│       └── EXCEPTIONS.md
├── addons/                         ← módulos Odoo (Odoo Apps)
│   ├── odoocarriers_base/
│   ├── delivery_dpd_europe/
│   └── delivery_dpd_{de,fr,nl,be,uk}/
├── carrier_gateway/                ← backend (nome alvo)
├── deploy/
└── scripts/
```

---

## 4. Primeira etapa (pipeline técnico)

Começar com **uma** divisão nacional DPD; domínio interno já multipaís (mesmo modelo; adaptadores por país).

```
Pedido Odoo → Modelo DPD normalizado → Adaptador do país → API nacional DPD
```

O modelo comum inclui: remetente/destinatário, volumes, peso/dimensões, serviço, pickup, COD, seguro, customs, etiqueta/coleta/manifesto/tracking/devolução. Adaptadores traduzem; Odoo não vê SOAP/REST nacional.

---

## 5. Modelo normalizado (domínio)

```mermaid
classDiagram
    class Shipment {
        +string connection_ref
        +Address shipper
        +Address recipient
        +Parcel[] parcels
        +string service_code
        +PickupPoint pickup
        +Money cod
        +bool insurance
        +Customs customs
    }
    class ShipmentResult {
        +string shipment_ref
        +string tracking_number
        +Label label
        +string status
    }
    class ExceptionRecord {
        +string category
        +string severity
        +string message
        +string suggested_action
    }
```

---

## 6. Onboarding no Odoo

```mermaid
flowchart TD
    A[Instalar_modulo] --> B[IAP_conta_automatica]
    B --> C[Detectar_pais_armazem]
    C --> D[Escolher_operacao_DPD]
    D --> E[Informar_credenciais]
    E --> F[Teste_no_gateway]
    F -->|Erro| G[Mensagem_acionavel]
    G --> E
    F -->|OK| H[Sincronizar_servicos]
    H --> I[Criar_metodos_entrega]
    I --> J[Remessa_teste_etiqueta]
    J --> K[Producao]
```

Detalhamento: [operations/ONBOARDING.md](./operations/ONBOARDING.md).

---

## 7. Painel de exceções

```mermaid
stateDiagram-v2
    [*] --> Detectada
    Detectada --> Retentativa: falha_transitoria
    Retentativa --> Resolvida: sucesso
    Retentativa --> Aberta: falha_persistente
    Aberta --> EmAnalise
    EmAnalise --> Resolvida
    Aberta --> Ignorada
    Resolvida --> Reaberta: recorrencia
```

| Severidade | Exemplos |
|------------|----------|
| Crítica | Credencial expirada, IAP sem crédito |
| Alta | Endereço recusado, serviço indisponível |
| Média | Tracking parado |
| Info | Atraso previsto |

Detalhamento: [operations/EXCEPTIONS.md](./operations/EXCEPTIONS.md).

---

## 8. Distribuição comercial

```mermaid
flowchart LR
    subgraph apps [Odoo_Apps_Store]
        L1[DPD_Germany]
        L2[DPD_France]
        L3[DPD_Benelux]
        L4[DPD_UK]
        L5[DPD_Europe]
    end
    subgraph pay [Odoo_IAP]
        P1[Pacote_anual]
        P2[Creditos_por_remessa]
    end
    apps --> pay
    pay --> GW[Mesmo_gateway]
```

Listagens por país + pacote Europe. Módulo base acessível; receita principal via IAP. Um backend, uma carteira de créditos.

---

## 9. Escopo geográfico (5 APIs)

| Código | Operador | Sandbox |
|--------|----------|---------|
| de | DPD eSolutions / Web Connect | Registo desenvolvedor DE |
| fr | DPD France (SOAP) | Conta cliente + IP whitelist |
| nl | DPD NL REST | Stage credentials |
| be | DPD Belux SOAP | Separado de NL |
| uk | DPD UK API | Chaves sandbox no portal |

Benelux: **NL e BE são adaptadores distintos**.

---

## 10. Fora de escopo (v1)

- Portal SaaS, Supabase, Stripe do HubCarrier legado
- UPS / DHL neste repositório
- Odoo Online (SaaS odoo.com) — sem módulos Python de terceiros

---

## 11. Ordem de implementação

```mermaid
gantt
    title Roadmap_tecnico
    dateFormat YYYY-MM-DD
    section Base
    odoocarriers_base_IAP           :a1, 2026-01-01, 14d
    Gateway_esqueleto_health        :a2, after a1, 7d
    section MVP
    Adaptador_pais_1                :b1, after a2, 21d
    Onboarding_primeira_etiqueta    :b2, after b1, 7d
    section Operacao
    Excecoes_tracking               :c1, after b2, 14d
    NL_BE_UK                        :c2, after c1, 30d
    section Go_to_market
    Odoo_Apps_listagens             :d1, after b2, 14d
```

Sequência lógica:

1. `odoocarriers_base` + gateway mínimo + IAP  
2. Um país MVP (credenciais sandbox)  
3. Exceções e tracking operacional  
4. Demais países  
5. Publicação Odoo Apps  

Estado vs código: [ROADMAP_IMPLEMENTACAO.md](./ROADMAP_IMPLEMENTACAO.md).

---

## 12. Migração HubCarrier

Código Odoo legado pode alimentar `addons/odoocarriers_base` desde que:

- removidos fluxo SaaS, **token manual** e URLs do backend antigo;
- chamadas HTTP centralizadas em `gateway_client`;
- credenciais **apenas** no gateway.

O módulo [`shipping_hub_connector`](../shipping_hub_connector/) actua como **ponte** até `odoocarriers_base` + `delivery_dpd_*` estarem disponíveis.
