#!/usr/bin/env bash
# Aplica DDL OdooCarriers no MySQL do servidor de testes (Hetzner).
#
# Este script corre na máquina de dev e, via SSH (host predefinido: dev), executa
# mysql em 127.0.0.1:3306 *no servidor* — credenciais em ~/odoocarriers/hub-gateway/.env
# remoto (DB_PASSWORD com $ ou espaços deve ir entre aspas simples para `source` em bash).
#
# Não é necessário túnel SSH local para aplicar o schema. O túnel
# (scripts/mysql-tunnel-dev.sh) só serve para correr o hub-gateway *localmente*
# contra o MySQL remoto: DB_HOST=127.0.0.1 DB_PORT=3307 na máquina de dev.
#
# Variável opcional: ODOOCARRIERS_SSH_HOST (predefinição: dev).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOST="${ODOOCARRIERS_SSH_HOST:-dev}"
SQL_DIR="${ROOT}/docs/sql"

for f in setup_odoocarriers_saas.sql odoocarriers_schema.sql; do
  [[ -f "${SQL_DIR}/${f}" ]] || { echo "Erro: ${SQL_DIR}/${f} em falta." >&2; exit 1; }
done

echo "==> Bootstrap database (sudo mysql no ${REMOTE_HOST})"
ssh -o BatchMode=yes "${REMOTE_HOST}" "sudo mysql" < "${SQL_DIR}/setup_odoocarriers_saas.sql" || \
  echo "AVISO: bootstrap falhou (sudo?) — assumindo BD já existe."

echo "==> Schema odoocarriers"
ssh -o BatchMode=yes "${REMOTE_HOST}" \
  'set -a && source "${HOME}/odoocarriers/hub-gateway/.env" && set +a && mysql -h 127.0.0.1 -u "${DB_USERNAME}" -p"${DB_PASSWORD}" "${DB_DATABASE}"' \
  < "${SQL_DIR}/odoocarriers_schema.sql"

MIG="${SQL_DIR}/migrations/002_connections_and_uuid.sql"
if [[ -f "${MIG}" ]]; then
  echo "==> Migration 002 (uuid + connections)"
  ssh -o BatchMode=yes "${REMOTE_HOST}" \
    'set -a && source "${HOME}/odoocarriers/hub-gateway/.env" && set +a && mysql -h 127.0.0.1 -u "${DB_USERNAME}" -p"${DB_PASSWORD}" "${DB_DATABASE}"' \
    < "${MIG}" || echo "AVISO: migration 002 falhou (colunas já existem?)"
fi

echo "==> Tabelas"
ssh -o BatchMode=yes "${REMOTE_HOST}" \
  'set -a && source "${HOME}/odoocarriers/hub-gateway/.env" && set +a && mysql -h 127.0.0.1 -u "${DB_USERNAME}" -p"${DB_PASSWORD}" "${DB_DATABASE}" -e "SHOW TABLES;"' \
  2>&1 | grep -v Warning || true

echo "Concluído."
