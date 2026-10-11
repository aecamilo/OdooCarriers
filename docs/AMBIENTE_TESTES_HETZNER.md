# Ambiente de testes — Hetzner (Hub Gateway)

> **Odoo** corre **apenas na máquina local** (Docker).  
> O servidor Hetzner hospeda o **serviço de gestão da integração** (Hub Gateway Python).  
> Instâncias Odoo em teste apontam o URL do gateway para este servidor.

Versão: 1.0 · 2026-10-11

---

## Papéis

| Componente | Onde corre | Função |
|------------|------------|--------|
| Odoo 17 + `shipping_hub_connector` | **Máquina local** | ERP, credenciais carrier, chamadas HTTPS ao gateway |
| **Hub Gateway** (FastAPI) | **Hetzner** (`~/odoocarriers/hub-gateway`) | Labels, provision, IAP, quotas |
| **MySQL** `odoocarriers` | **Hetzner** (user `saas`) | Dados do gateway de validação |
| MySQL `saastip` | Hetzner (legado/outros) | **Não** usar para OdooCarriers |

Fluxo: Odoo (local ou futuros clientes) → **HTTPS** → gateway no Hetzner → APIs carrier (transitório).

---

## Servidor Hetzner

| Campo | Valor |
|-------|--------|
| Fornecedor | Hetzner Cloud |
| Hostname | `uAlexanderCX21` |
| IP público | `142.132.191.87` |
| SO | Ubuntu 24.04.3 LTS (Noble), aarch64 |
| SSH (local) | `~/.ssh/config` → Host **`dev`** |
| Utilizador SSH | `alexander` |
| Chave | `~/.ssh/id_ed25519` |
| Stack web | Nginx 1.24 → uvicorn `127.0.0.1:8000`; systemd `odoocarriers-gateway.service` |
| MySQL | 8.0.x |

---

## Directório exclusivo OdooCarriers

No servidor (utilizador `alexander`):

```text
/home/alexander/odoocarriers/
  hub-gateway/          # código deployado + .env (não versionado)
    app/                # FastAPI (quando implementado)
    logs/
    .env                # credenciais MySQL + URLs (chmod 600)
```

**Não** misturar com `/var/www/html/stip` nem com a base `saastip`.

---

## Base de dados de validação

| Campo | Valor |
|-------|--------|
| Nome | **`odoocarriers`** |
| Utilizador | **`saas`** |
| Password | Gestor de secrets / `.env` no servidor (não versionar) |
| Recriação DDL | [sql/setup_odoocarriers_saas.sql](./sql/setup_odoocarriers_saas.sql) |

O gateway no servidor liga a `127.0.0.1:3306`. Na máquina de dev, use o [túnel SSH](./scripts/mysql-tunnel-dev.sh) (`DB_PORT=3307`) — **apenas** para gateway local ou cliente SQL na máquina de dev.

### Aplicar schema / migrations (sem túnel local)

Na máquina de desenvolvimento:

```bash
./scripts/apply-odoocarriers-db.sh
```

O script faz SSH ao host `dev` e corre `mysql` em **127.0.0.1:3306 no servidor**, usando o `.env` em `~/odoocarriers/hub-gateway/.env`. **Não** precisa de `./scripts/mysql-tunnel-dev.sh`.

No `.env` remoto, valores com `$` (ex.: password) devem estar entre **aspas simples** para o `source` em bash usado pelo script.



> A base `odoocarriers_hub` (user dedicado) foi substituída por `odoocarriers` + `saas`.

---



---

## Gateway em execução (Nginx + systemd)

| Item | Valor |
|------|--------|
| Unit systemd | `odoocarriers-gateway.service` |
| Processo | `uvicorn app.main:app` em `127.0.0.1:8000` |
| Venv | `~/odoocarriers/hub-gateway/.venv` |
| Templates no repo | `deploy/server/*.nginx`, `deploy/server/odoocarriers-gateway.service` |
| Health | `GET /healthz` |

### URL pública (Odoo → Gateway)

| Endpoint | Uso |
|----------|-----|
| **`https://stip.pt/hub-test/`** | HTTPS activo (certificado `stip.pt`); usar como **Gateway URL** no Odoo enquanto não existir DNS dedicado |
| **`https://hub-test.stip.pt/`** | Vhost Nginx em `:80` preparado; falta registo **DNS A** → `142.132.191.87`, depois `sudo certbot --nginx -d hub-test.stip.pt` |

Após deploy de código:

```bash
./scripts/deploy-gateway-to-test.sh
ssh dev 'sudo systemctl restart odoocarriers-gateway.service'
```

## Túnel SSH (dev local → MySQL remoto)

Para testar o gateway **na máquina de desenvolvimento** contra a mesma base do servidor:

1. Activar o túnel (deixar o terminal aberto):

   ```bash
   ./scripts/mysql-tunnel-dev.sh
   ```

   Predefinição: `localhost:3307` → MySQL `127.0.0.1:3306` no host `dev`.

2. No `hub-gateway/.env` **local**, enquanto o túnel estiver activo:

   ```env
   DB_HOST=127.0.0.1
   DB_PORT=3307
   DB_DATABASE=odoocarriers
   DB_USERNAME=saas
   DB_PASSWORD='<copiar do .env do servidor; aspas simples se tiver $>'
   ```

Para copiar só a password do servidor (não versionar):  
`ssh dev "grep ^DB_PASSWORD= ~/odoocarriers/hub-gateway/.env"` → colar no `.env` local.

Variáveis opcionais: `ODOOCARRIERS_MYSQL_LOCAL_PORT`, `ODOOCARRIERS_SSH_HOST`.

---

## Deploy do gateway após cada actualização

Sempre que alterar `hub-gateway/` no repositório, publicar no servidor de testes:

```bash
./scripts/deploy-gateway-to-test.sh
```

- Sincroniza via `rsync` para `dev:~/odoocarriers/hub-gateway/`.
- **Não** sobrescreve o `.env` remoto.
- Após deploy, reiniciar o processo do gateway no servidor (systemd ou uvicorn — quando configurado).

**Gateway URL** no Odoo: `https://stip.pt/hub-test` (ou `https://hub-test.stip.pt` após DNS + Certbot). Alinhar com `APP_PUBLIC_URL` no `.env` remoto.

---

## Odoo local

1. Instalar/atualizar módulo: `shipping_hub_connector/install.sh` (Docker local).
2. Definir **Gateway URL** para o endpoint HTTPS do servidor de testes (não `localhost`, excepto se fizer proxy manual).
3. Para E2E só com simulador: no `.env` **remoto**, `GATEWAY_CARRIER_SIMULATOR=true` (nunca em produção comercial).

---

## Histórico

| Data | Alteração |
|------|-----------|
| 2026-10-11 | Estrutura `~/odoocarriers`, BD `odoocarriers_hub`, scripts túnel/deploy |
| 2026-10-11 | BD `odoocarriers` (saas); systemd + Nginx; URL `https://stip.pt/hub-test` |
