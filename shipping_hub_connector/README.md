# Shipping Hub Connector (Odoo 17)

Official Odoo addon for the **European Shipping Hub** SaaS — generate carrier labels from delivery orders (DHL, DPD, GLS, and other European carriers supported by your Hub account).

**Module technical name:** `shipping_hub_connector`

---

## Requirements

- Odoo **17.0** with **Inventory** and **Delivery - Stock** (`stock_delivery`; usually auto-installed with Sales + Inventory)
- HTTPS outbound from the Odoo server to the Shipping Hub Gateway
- **Test setup:** Odoo runs **locally**; point **Gateway URL** to the Hetzner test server (see [AMBIENTE_TESTES_HETZNER.md](../docs/AMBIENTE_TESTES_HETZNER.md))
- On the Odoo host: `pip install -r requirements.txt` (`requests`, `pypdf`)
- Active **Shipping Hub** subscription and **API token** from the customer portal

---

## Instalação rápida (Linux)

1. Extraia o ZIP e entre na pasta do módulo:
   ```bash
   unzip shipping_hub_connector.zip
   cd shipping_hub_connector
   chmod +x install.sh
   ./install.sh
   ```
2. O script **descobre automaticamente** (Docker: contentores Odoo em execução, diretório Compose, serviço `web`, volume `extra-addons`, base PostgreSQL via `psql -l`; nativo: caminhos comuns e systemd). Só pede escolha se existirem **várias instalações** ou **várias bases**; caso contrário mostra um resumo e pede **Confirma instalação com estes valores? [S/n]** (Enter = sim).
3. Copia o módulo, instala `requirements.txt`, executa `odoo -u shipping_hub_connector`, verifica o esquema e reinicia o serviço.

Variáveis `SHIPPING_HUB_*` continuam a **substituir** a descoberta (útil em CI). Com `SHIPPING_HUB_NONINTERACTIVE=1` usa o melhor candidato sem confirmação.

**Modo não interativo (Docker, exemplo):**
```bash
export SHIPPING_HUB_INSTALL_MODE=docker
export SHIPPING_HUB_COMPOSE_DIR="$HOME/odoo-dev"
export SHIPPING_HUB_ADDONS_DIR="$HOME/odoo-dev/custom_addons"
export SHIPPING_HUB_DB=odoo_shipping_test
export SHIPPING_HUB_NONINTERACTIVE=1
./install.sh
```

Variáveis opcionais: `SHIPPING_HUB_WEB_SERVICE`, `SHIPPING_HUB_DB_SERVICE`, `SHIPPING_HUB_PGUSER`, `SHIPPING_HUB_ODOO_BIN`, `SHIPPING_HUB_SYSTEMD`, `SHIPPING_HUB_VENV`.

### Troubleshooting: `UndefinedColumn` on `shipping_hub_*`

If opening a sale order or delivery fails with PostgreSQL **`column stock_picking.shipping_hub_… does not exist`**, the Python module is newer than the database schema. **Upgrade the module** on that database (replace `odoo_shipping_test` with your DB name):

```bash
cd ~/odoo-dev
docker compose stop web
docker compose run --rm --no-deps web odoo -u shipping_hub_connector -d odoo_shipping_test --stop-after-init
docker compose up -d
```

Or re-run `./install.sh` with `SHIPPING_HUB_DB` set. After upgrade, `install.sh` verifies that `stock_picking.shipping_hub_number_of_packages` exists.

---

## 1. Installation from ZIP (Docker / VPS)

1. Extract **`shipping_hub_connector`** from the ZIP into your Odoo **extra-addons** path (e.g. `/mnt/extra-addons/` or `/opt/odoo/extra-addons/`).
2. Install Python dependencies **inside the Odoo container or venv**:
   ```bash
   pip install -r /mnt/extra-addons/shipping_hub_connector/requirements.txt
   ```
3. Restart Odoo.
4. **Settings → Activate Developer Mode → Apps → Update Apps List**.
5. Install **Shipping Hub Connector - European Logistics** (or **Upgrade** if already installed).
6. **Inventory → Configuration → Settings → Shipping Hub Connector** — API token, environment. Default sandbox gateway: `https://stip.pt/hub-test` (override optional).

---

## 2. Installation — Odoo.sh

1. Add the **`shipping_hub_connector`** folder to the Git repository linked to your Odoo.sh project.
2. Commit and push; Odoo.sh detects the addon on the next build.
3. Update the apps list on the instance and **Install** the module.
4. Configure the API token in Inventory settings.

---

## End-to-end test (sale → label)

1. **Delivery method:** Inventory → Configuration → Delivery Methods → create carrier with provider **Shipping Hub Europe**, hub carrier code (e.g. DHL Express), service level.
2. **Settings:** paste API token, **Test connection**, enable auto-generate / attach PDF if desired.
3. **Sale order:** confirm order, ensure outgoing delivery is **Ready** (`assigned`) or **Done**.
4. On the delivery order: set **Carrier**, **Shipping weight** (required if products have no weight), **Number of packages** (default 1).
5. Click **Generate Hub Label** (or validate picking if auto-generate is on).
6. Expect **Tracking** on the picking and PDF in Chatter when attach is enabled.

### Verify the full flow without signing up at DHL/DPD/GLS

Gateway **integration simulator** — one env flag for **all** carrier codes:

1. Gateway `.env`: `GATEWAY_CARRIER_SIMULATOR=true` (never in production).
2. Restart gateway. No MyDHL/DPD developer signup; Hub subscription + Odoo API token still required.
3. Generate Hub Label → tracking `SIM-…` + PDF in Chatter = full Odoo ↔ Hub path OK.
4. For go-live: set simulator `false` and configure **only the carriers you sell** (not every carrier).

7. **Batch:** select multiple pickings in list view → **Action → Generate Hub Labels (batch)**.

---

## Languages

`i18n/`: English, German, French, Italian, Spanish, Portuguese, Polish, Dutch.  
After upgrade: `-u shipping_hub_connector` to reload translations.

---

## License

**OPL-1** — commercial use per your Shipping Hub agreement.
