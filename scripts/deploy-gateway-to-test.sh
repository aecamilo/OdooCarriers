#!/usr/bin/env bash
# Publica o código hub-gateway no servidor de testes (Hetzner).
# Não sobrescreve .env remoto (segredos ficam só no servidor).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOST="${ODOOCARRIERS_SSH_HOST:-dev}"
REMOTE_DIR="${ODOOCARRIERS_REMOTE_DIR:-odoocarriers/hub-gateway}"

if [[ ! -d "${ROOT}/hub-gateway" ]]; then
  echo "Erro: ${ROOT}/hub-gateway não existe." >&2
  exit 1
fi

echo "Deploy → ${REMOTE_HOST}:~/${REMOTE_DIR}/"
rsync -avz --delete \
  --exclude '.env' \
  --exclude '__pycache__/' \
  --exclude '.venv/' \
  --exclude '*.pyc' \
  "${ROOT}/hub-gateway/" "${REMOTE_HOST}:${REMOTE_DIR}/"

echo "Concluído. No servidor: sudo systemctl restart odoocarriers-gateway.service"
