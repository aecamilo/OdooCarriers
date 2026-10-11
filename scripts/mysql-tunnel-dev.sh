#!/usr/bin/env bash
# Túnel SSH: MySQL do servidor de testes (127.0.0.1:3306) → localhost:3307 na máquina de dev.
# Manter este processo aberto enquanto corre o gateway local ou ferramentas SQL contra a BD de validação.
set -euo pipefail

LOCAL_PORT="${ODOOCARRIERS_MYSQL_LOCAL_PORT:-3307}"
REMOTE_HOST="${ODOOCARRIERS_SSH_HOST:-dev}"

echo "Túnel MySQL: localhost:${LOCAL_PORT} → ${REMOTE_HOST}:127.0.0.1:3306"
echo "Gateway local: DB_HOST=127.0.0.1 DB_PORT=${LOCAL_PORT} (ver hub-gateway/.env)"
echo "Ctrl+C para encerrar."

exec ssh -N -L "${LOCAL_PORT}:127.0.0.1:3306" "${REMOTE_HOST}"
