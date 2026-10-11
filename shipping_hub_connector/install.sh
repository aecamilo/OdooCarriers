#!/usr/bin/env bash
# Instalação Linux do módulo shipping_hub_connector (Odoo 17).
# Executar a partir da pasta extraída do ZIP: ./install.sh
# Se o utilizador não estiver no grupo docker: sudo ./install.sh
set -euo pipefail

MODULE_NAME="shipping_hub_connector"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$SCRIPT_DIR"

# Variáveis de ambiente (modo não interativo / overrides — saltam descoberta quando definidas)
# SHIPPING_HUB_INSTALL_MODE=docker|bare
# SHIPPING_HUB_COMPOSE_DIR=   diretório com docker-compose.yml
# SHIPPING_HUB_ADDONS_DIR=    caminho no host para extra-addons
# SHIPPING_HUB_DB=            nome da base de dados Odoo
# SHIPPING_HUB_WEB_SERVICE=   serviço web no compose (predef.: web)
# SHIPPING_HUB_DB_SERVICE=    serviço Postgres no compose (predef.: db)
# SHIPPING_HUB_PGUSER=          utilizador Postgres (predef.: odoo)
# SHIPPING_HUB_ODOO_BIN=      binário odoo (bare metal)
# SHIPPING_HUB_SYSTEMD=       unidade systemd (bare metal, opcional)
# SHIPPING_HUB_GATEWAY_URL=   URL do hub-gateway (ex.: https://stip.pt/hub-test)
# SHIPPING_HUB_API_TOKEN=     token API (pós scripts/seed-dev-account.sh)
# SHIPPING_HUB_ENVIRONMENT=     sandbox|production
# SHIPPING_HUB_SKIP_IAP_CHARGE= True|False
# SHIPPING_HUB_NONINTERACTIVE=1  usa melhor candidato, confirmações automáticas (yes)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*" >&2; }
log_warn()  { echo -e "${YELLOW}[AVISO]${NC} $*" >&2; }
log_err()   { echo -e "${RED}[ERRO]${NC} $*" >&2; }

INSTALL_CONFIRMED=0

# Docker: muitas instalações Linux exigem sudo (utilizador fora do grupo docker).
DOCKER_PREFIX=()

init_docker_cli() {
  DOCKER_PREFIX=()
  if [[ "$(id -u)" -eq 0 ]]; then
    DOCKER_PREFIX=(docker)
    return 0
  fi
  command -v docker &>/dev/null || return 1
  if docker info &>/dev/null 2>&1; then
    DOCKER_PREFIX=(docker)
    return 0
  fi
  if sudo -n docker info &>/dev/null 2>&1; then
    DOCKER_PREFIX=(sudo docker)
    log_info "Docker via sudo (credencial já em cache)."
    return 0
  fi
  if sudo docker info &>/dev/null 2>&1; then
    DOCKER_PREFIX=(sudo docker)
    log_info "Docker detetado via sudo (socket não acessível sem elevação)."
    return 0
  fi
  DOCKER_PREFIX=(docker)
  return 1
}

docker_cli() {
  "${DOCKER_PREFIX[@]}" "$@"
}


confirm_yes_default() {
  local msg="$1"
  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    return 0
  fi
  read -r -p "$msg [S/n]: " ans
  [[ -z "$ans" || "${ans,,}" == "s" || "${ans,,}" == "sim" || "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

confirm() {
  local msg="$1"
  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    return 0
  fi
  read -r -p "$msg [s/N]: " ans
  [[ "${ans,,}" == "s" || "${ans,,}" == "sim" || "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

prompt_default() {
  local var_name="$1"
  local prompt_text="$2"
  local default_val="$3"
  if [[ -n "${!var_name:-}" ]]; then
    echo "${!var_name}"
    return
  fi
  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    echo "$default_val"
    return
  fi
  read -r -p "$prompt_text [$default_val]: " ans
  echo "${ans:-$default_val}"
}

compose_cmd() {
  _compose_cmd_with_prefix "$@" && return 0
  if [[ " ${DOCKER_PREFIX[*]} " != *" sudo "* ]]; then
    sudo docker compose "$@" && return 0
    sudo docker-compose "$@" 2>/dev/null && return 0
  fi
  return 1
}

_compose_cmd_with_prefix() {
  if "${DOCKER_PREFIX[@]}" compose version &>/dev/null 2>&1; then
    "${DOCKER_PREFIX[@]}" compose "$@"
    return $?
  fi
  if [[ " ${DOCKER_PREFIX[*]} " == *" sudo "* ]] && sudo docker-compose version &>/dev/null 2>&1; then
    sudo docker-compose "$@"
    return $?
  fi
  if command -v docker-compose &>/dev/null; then
    docker-compose "$@"
    return $?
  fi
  "${DOCKER_PREFIX[@]}" compose "$@"
}

docker_available() {
  command -v docker &>/dev/null && "${DOCKER_PREFIX[@]}" info &>/dev/null 2>&1
}

list_running_odoo_containers() {
  docker_available || return 0
  docker_cli ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.service"}}\t{{.Label "com.docker.compose.project.working_dir"}}' 2>/dev/null \
    | while IFS=$'\t' read -r cid cname cimage proj svc wdir; do
        [[ -z "$cid" ]] && continue
        # Nunca tratar Postgres / serviço "db" como contentor Odoo (não tem pip nem odoo).
        [[ "$cimage" =~ [Pp]ostgres ]] && continue
        [[ "${svc:-}" == "db" ]] && continue
        [[ "$cname" =~ -db- ]] && continue
        if [[ "$cimage" =~ [Oo]doo ]] || [[ "$cname" =~ -web- ]] || [[ "${svc:-}" == "web" ]]; then
          printf '%s|%s|%s|%s|%s|%s\n' "$cid" "$cname" "$cimage" "${proj:-}" "${svc:-web}" "${wdir:-}"
        fi
      done
}

compose_dir_has_odoo_service() {
  local d="$1" f
  for f in "$d/docker-compose.yml" "$d/docker-compose.yaml" "$d/compose.yml"; do
    [[ -f "$f" ]] || continue
    if grep -qiE 'image:\s*["'\'']?[^"'\''[:space:]]*odoo|^[[:space:]]*odoo:' "$f" 2>/dev/null; then
      return 0
    fi
  done
  return 1
}

find_all_compose_dirs() {
  local candidates=()
  candidates+=("${SHIPPING_HUB_COMPOSE_DIR:-}")
  candidates+=("$PWD")
  candidates+=("$SCRIPT_DIR")
  candidates+=("$(dirname "$SCRIPT_DIR")")
  candidates+=("$HOME/odoo-dev")
  candidates+=("$HOME/odoo")
  candidates+=("/opt/odoo")

  local seen="" d="$SCRIPT_DIR"
  while [[ "$d" != "/" ]]; do
    candidates+=("$d")
    d="$(dirname "$d")"
  done

  for d in "${candidates[@]}"; do
    [[ -z "$d" || ! -d "$d" ]] && continue
    d="$(cd "$d" && pwd)"
    [[ "$seen" == *"|$d|"* ]] && continue
    seen="${seen}|$d|"
    compose_dir_has_odoo_service "$d" && echo "$d"
  done
}

detect_addons_from_compose_file() {
  local compose_dir="$1"
  local compose_file=""
  for f in "$compose_dir/docker-compose.yml" "$compose_dir/docker-compose.yaml" "$compose_dir/compose.yml"; do
    [[ -f "$f" ]] && compose_file="$f" && break
  done
  [[ -z "$compose_file" ]] && return 1

  local line host_path rel
  while IFS= read -r line; do
    if [[ "$line" =~ extra-addons|custom_addons ]]; then
      if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*([^:]+):[^:]*extra-addons ]]; then
        host_path="${BASH_REMATCH[1]}"
        host_path="${host_path#\"}"; host_path="${host_path%\"}"
        host_path="${host_path#\'}"; host_path="${host_path%\'}"
        if [[ "$host_path" != /* ]]; then
          host_path="$compose_dir/$host_path"
        fi
        if [[ -d "$host_path" ]]; then
          echo "$(cd "$host_path" && pwd)"
          return 0
        elif [[ -d "$(dirname "$host_path")" ]]; then
          mkdir -p "$host_path"
          echo "$(cd "$host_path" && pwd)"
          return 0
        fi
      fi
    fi
  done < "$compose_file"
  return 1
}

detect_web_service() {
  local compose_dir="$1"
  local compose_file=""
  for f in "$compose_dir/docker-compose.yml" "$compose_dir/docker-compose.yaml" "$compose_dir/compose.yml"; do
    [[ -f "$f" ]] && compose_file="$f" && break
  done
  [[ -z "$compose_file" ]] && { echo "web"; return; }

  if grep -qE '^[[:space:]]*web:' "$compose_file"; then
    echo "web"
    return
  fi
  echo "web"
}

detect_db_service() {
  local compose_dir="$1"
  if [[ -n "${SHIPPING_HUB_DB_SERVICE:-}" ]]; then
    echo "$SHIPPING_HUB_DB_SERVICE"
    return
  fi
  local compose_file=""
  for f in "$compose_dir/docker-compose.yml" "$compose_dir/docker-compose.yaml" "$compose_dir/compose.yml"; do
    [[ -f "$f" ]] && compose_file="$f" && break
  done
  [[ -z "$compose_file" ]] && { echo "db"; return; }

  if grep -qE '^[[:space:]]*db:' "$compose_file"; then
    echo "db"
    return
  fi
  echo "db"
}

detect_db_from_env() {
  local compose_dir="$1"
  local env_file db
  for env_file in "$compose_dir/.env" "$compose_dir/.env.local"; do
    if [[ -f "$env_file" ]]; then
      db=$(grep -E '^SHIPPING_HUB_DB=|^ODOO_DB=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
      [[ -n "$db" ]] && { echo "$db"; return 0; }
    fi
  done
  return 1
}


detect_addons_from_compose_config() {
  local compose_dir="$1"
  [[ -d "$compose_dir" ]] || return 1
  local out line host_path target=""
  out="$( ( cd "$compose_dir" && compose_cmd config 2>/dev/null ) )" || return 1
  while IFS= read -r line; do
    if [[ "$line" =~ target:[[:space:]]*/mnt/extra-addons ]]; then
      target="/mnt/extra-addons"
      continue
    fi
    if [[ -n "$target" && "$line" =~ ^[[:space:]]*source:[[:space:]]*(.+)$ ]]; then
      host_path="${BASH_REMATCH[1]}"
      host_path="${host_path#\"}"; host_path="${host_path%\"}"
      if [[ "$host_path" != /* ]]; then
        host_path="$compose_dir/$host_path"
      fi
      if [[ -d "$host_path" ]]; then
        echo "$(cd "$host_path" && pwd)"
        return 0
      fi
      target=""
    fi
    if [[ "$line" =~ target: ]]; then
      target=""
    fi
  done <<< "$out"
  return 1
}

detect_addons_from_container() {
  local container_id="$1"
  [[ -n "$container_id" ]] || return 1
  local mounts src dest
  mounts="$(docker_cli inspect -f '{{range .Mounts}}{{.Source}}|{{.Destination}}{{"\n"}}{{end}}' "$container_id" 2>/dev/null)" || return 1
  while IFS='|' read -r src dest; do
    [[ -z "$src" ]] && continue
    if [[ "$dest" == "/mnt/extra-addons" || "$dest" == *extra-addons* ]]; then
      if [[ -d "$src" ]]; then
        echo "$(cd "$src" && pwd)"
        return 0
      fi
    fi
  done <<< "$mounts"
  return 1
}


list_odoo_databases_from_filestore() {
  local web_cid="$1"
  [[ -n "$web_cid" ]] || return 1
  local path line
  for path in "/var/lib/odoo/.local/share/Odoo/filestore" "/var/lib/odoo/filestore"; do
    while IFS= read -r line; do
      [[ -n "$line" && "$line" != "." && "$line" != ".." ]] && echo "$line"
    done < <(docker_cli exec "$web_cid" sh -c "ls -1 '$path' 2>/dev/null" || true)
  done | sort -u
}

find_db_container_by_web_name() {
  local web_cname="$1"
  local prefix cid
  if [[ "$web_cname" =~ ^(.+)-web-[0-9]+$ ]]; then
    prefix="${BASH_REMATCH[1]}"
    cid="$(docker_cli ps -q --filter "name=${prefix}-db-" 2>/dev/null | head -1)" || true
    [[ -n "$cid" ]] && echo "$cid" && return 0
  fi
  return 1
}

list_odoo_databases_docker() {
  local compose_dir="$1"
  local db_svc="$2"
  local pg_user="${SHIPPING_HUB_PGUSER:-odoo}"
  ( cd "$compose_dir" && compose_cmd exec -T "$db_svc" psql -U "$pg_user" -lqt 2>/dev/null ) \
    | awk -F'|' '{gsub(/ /,"",$1); if ($1 != "" && $1 !~ /^(template0|template1|postgres)$/) print $1}'
}

count_tables_in_db() {
  local compose_dir="$1"
  local db_svc="$2"
  local db_name="$3"
  local pg_user="${SHIPPING_HUB_PGUSER:-odoo}"
  ( cd "$compose_dir" && compose_cmd exec -T "$db_svc" \
    psql -U "$pg_user" -d "$db_name" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null ) \
    | tr -d '[:space:]'
}

find_db_container_for_project() {
  local project="$1"
  local compose_dir="$2"
  local line cid cname cimage proj svc
  while IFS=$'\t' read -r cid cname cimage proj svc; do
    [[ -z "$cid" ]] && continue
    if [[ -n "$project" && "$proj" == "$project" && ( "$svc" == "db" || "$cimage" =~ postgres ) ]]; then
      echo "$cid"
      return 0
    fi
  done < <(docker_cli ps --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.service"}}' 2>/dev/null)
  local db_svc cid
  db_svc="$(detect_db_service "$compose_dir")"
  cid="$( ( cd "$compose_dir" && compose_cmd ps -q "$db_svc" 2>/dev/null ) | head -1 )" || true
  [[ -n "$cid" ]] && echo "$cid"
}

postgres_user_from_container() {
  local cid="$1"
  docker_cli inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$cid" 2>/dev/null \
    | grep -E '^POSTGRES_USER=' | head -1 | cut -d= -f2-
}

pick_database_name() {
  local compose_dir="$1"
  local db_svc="$2"
  local web_cid="${3:-}"
  local web_cname="${4:-}"
  local -a dbs=()
  local db line db_cid pg_user default_db

  if [[ -n "${SHIPPING_HUB_DB:-}" ]]; then
    echo "$SHIPPING_HUB_DB"
    return 0
  fi

  db="$(detect_db_from_env "$compose_dir" || true)"
  if [[ -n "$db" ]]; then
    echo "$db"
    return 0
  fi

  while IFS= read -r line; do
    [[ -n "$line" ]] && dbs+=("$line")
  done < <(list_odoo_databases_docker "$compose_dir" "$db_svc")

  if [[ ${#dbs[@]} -eq 0 ]]; then
    db_cid="$(find_db_container_for_project "" "$compose_dir" | head -1)" || true
    if [[ -n "$db_cid" ]]; then
      pg_user="$(postgres_user_from_container "$db_cid")"
      [[ -n "$pg_user" ]] && SHIPPING_HUB_PGUSER="$pg_user"
      while IFS= read -r line; do
        [[ -n "$line" ]] && dbs+=("$line")
      done < <(docker_cli exec "$db_cid" psql -U "${SHIPPING_HUB_PGUSER:-odoo}" -lqt 2>/dev/null \
        | awk -F'|' '{gsub(/ /,"",$1); if ($1 != "" && $1 !~ /^(template0|template1|postgres)$/) print $1}')
    fi
  fi

  if [[ ${#dbs[@]} -eq 0 && -n "$web_cname" ]]; then
    db_cid="$(find_db_container_by_web_name "$web_cname" || true)"
    if [[ -n "$db_cid" ]]; then
      pg_user="$(postgres_user_from_container "$db_cid")"
      [[ -n "$pg_user" ]] && SHIPPING_HUB_PGUSER="$pg_user"
      while IFS= read -r line; do
        [[ -n "$line" ]] && dbs+=("$line")
      done < <(docker_cli exec "$db_cid" psql -U "${SHIPPING_HUB_PGUSER:-odoo}" -lqt 2>/dev/null         | awk -F'|' '{gsub(/ /,"",$1); if ($1 != "" && $1 !~ /^(template0|template1|postgres)$/) print $1}')
    fi
  fi

  if [[ ${#dbs[@]} -eq 0 && -n "$web_cid" ]]; then
    while IFS= read -r line; do
      [[ -n "$line" ]] && dbs+=("$line")
    done < <(list_odoo_databases_from_filestore "$web_cid")
  fi

  if [[ ${#dbs[@]} -eq 0 ]]; then
    log_warn "Não foi possível listar bases via Postgres (verifique sudo/docker). Indique o nome manualmente."
    if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
      echo "odoo_shipping_test"
      return 0
    fi
    echo "$(prompt_default SHIPPING_HUB_DB "Nome da base de dados Odoo" "odoo_shipping_test")"
    return 0
  fi

  if [[ ${#dbs[@]} -eq 1 ]]; then
    echo "${dbs[0]}"
    return 0
  fi

  local -a odoo_dbs=()
  for db in "${dbs[@]}"; do
    [[ "$db" =~ ^odoo ]] && odoo_dbs+=("$db")
  done

  if [[ ${#odoo_dbs[@]} -eq 1 ]]; then
    echo "${odoo_dbs[0]}"
    return 0
  fi

  local -a pick_list=("${dbs[@]}")
  [[ ${#odoo_dbs[@]} -gt 1 ]] && pick_list=("${odoo_dbs[@]}")

  if [[ ${#pick_list[@]} -eq 1 ]]; then
    echo "${pick_list[0]}"
    return 0
  fi

  local best="${pick_list[0]}" best_n=0 n
  for db in "${pick_list[@]}"; do
    n="$(count_tables_in_db "$compose_dir" "$db_svc" "$db" 2>/dev/null || echo 0)"
    [[ "${n:-0}" =~ ^[0-9]+$ ]] || n=0
    if (( n > best_n )); then
      best_n=$n
      best="$db"
    fi
  done

  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    echo "$best"
    return 0
  fi

  echo "" >&2
  log_info "Várias bases de dados encontradas:"
  local i=1
  for db in "${pick_list[@]}"; do
    echo "  $i) $db" >&2
    ((i++)) || true
  done
  echo "  (heurística sugere: $best)" >&2
  read -r -p "Usar BD ${best}? [S/n]: " ans
  if [[ -z "$ans" || "${ans,,}" == "s" || "${ans,,}" == "sim" || "${ans,,}" == "y" ]]; then
    echo "$best"
    return 0
  fi
  read -r -p "Escolha o número [1-${#pick_list[@]}]: " choice
  if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#pick_list[@]} )); then
    echo "${pick_list[$((choice-1))]}"
    return 0
  fi
  echo "$best"
}

declare -a DISCOVERY_CANDIDATES=()

build_docker_discovery() {
  DISCOVERY_CANDIDATES=()
  local -A seen_dirs=()

  while IFS='|' read -r cid cname cimage proj svc wdir; do
    [[ -z "$cid" ]] && continue
    local compose_dir="" web_svc="${svc:-}"

    if [[ -n "$wdir" && -d "$wdir" ]] && compose_dir_has_odoo_service "$wdir"; then
      compose_dir="$wdir"
    fi
    if [[ -z "$compose_dir" ]]; then
      wdir="$(docker_cli inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' "$cid" 2>/dev/null)" || true
      if [[ -n "$wdir" && -d "$wdir" ]] && compose_dir_has_odoo_service "$wdir"; then
        compose_dir="$wdir"
      fi
    fi
    [[ -z "$compose_dir" || ! -d "$compose_dir" ]] && continue
    compose_dir="$(cd "$compose_dir" && pwd)"
    [[ -n "${seen_dirs[$compose_dir]:-}" ]] && continue
    seen_dirs[$compose_dir]=1

    local odoo_cid="$cid"
    web_svc="$(detect_web_service "$compose_dir")"
    cid="$( ( cd "$compose_dir" && compose_cmd ps -q "$web_svc" 2>/dev/null ) | head -1 )" || true
    [[ -z "$cid" ]] && cid="$odoo_cid"
    DISCOVERY_CANDIDATES+=("${compose_dir}|${web_svc}|${cid}|${proj:-}")
  done < <(list_running_odoo_containers)

  while IFS= read -r d; do
    [[ -z "$d" ]] && continue
    [[ -n "${seen_dirs[$d]:-}" ]] && continue
    seen_dirs[$d]=1
    local web_svc cid
    web_svc="$(detect_web_service "$d")"
    cid="$( ( cd "$d" && compose_cmd ps -q "$web_svc" 2>/dev/null ) | head -1 )" || true
    DISCOVERY_CANDIDATES+=("${d}|${web_svc}|${cid}|")
  done < <(find_all_compose_dirs)
}

resolve_addons_dir() {
  local compose_dir="$1"
  local container_id="${2:-}"

  if [[ -n "${SHIPPING_HUB_ADDONS_DIR:-}" ]]; then
    echo "$SHIPPING_HUB_ADDONS_DIR"
    return 0
  fi

  local path=""
  path="$(detect_addons_from_compose_file "$compose_dir" || true)"
  [[ -n "$path" ]] && { echo "$path"; return 0; }

  path="$(detect_addons_from_compose_config "$compose_dir" || true)"
  [[ -n "$path" ]] && { echo "$path"; return 0; }

  if [[ -n "$container_id" ]]; then
    path="$(detect_addons_from_container "$container_id" || true)"
    [[ -n "$path" ]] && { echo "$path"; return 0; }
  fi

  local fallback="$compose_dir/custom_addons"
  if [[ -d "$fallback" ]]; then
    echo "$(cd "$fallback" && pwd)"
    return 0
  fi

  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    mkdir -p "$fallback"
    echo "$(cd "$fallback" && pwd)"
    return 0
  fi

  echo "$(prompt_default SHIPPING_HUB_ADDONS_DIR "Caminho no HOST para extra-addons (descoberta falhou)" "$fallback")"
}

pick_compose_candidate() {
  build_docker_discovery
  if [[ ${#DISCOVERY_CANDIDATES[@]} -eq 0 ]]; then
    return 1
  fi
  if [[ ${#DISCOVERY_CANDIDATES[@]} -eq 1 ]]; then
    echo "${DISCOVERY_CANDIDATES[0]}"
    return 0
  fi

  if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
    echo "${DISCOVERY_CANDIDATES[0]}"
    return 0
  fi

  echo "" >&2
  log_info "Várias instalações Docker/Compose detetadas:"
  local i=1 entry compose_dir web_svc
  for entry in "${DISCOVERY_CANDIDATES[@]}"; do
    IFS='|' read -r compose_dir web_svc _ _ <<< "$entry"
    echo "  $i) $compose_dir (serviço: $web_svc)" >&2
    ((i++)) || true
  done
  read -r -p "Escolha [1-${#DISCOVERY_CANDIDATES[@]}]: " choice
  if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#DISCOVERY_CANDIDATES[@]} )); then
    echo "${DISCOVERY_CANDIDATES[$((choice-1))]}"
    return 0
  fi
  echo "${DISCOVERY_CANDIDATES[0]}"
}

detect_bare_addons() {
  local candidates=(
    "/opt/odoo/extra-addons"
    "/usr/lib/python3/dist-packages/odoo/addons"
    "$HOME/odoo/addons"
    "$HOME/odoo-dev/custom_addons"
  )
  local c
  for c in "${candidates[@]}"; do
    [[ -d "$c" ]] && { echo "$c"; return 0; }
  done
  return 1
}

detect_bare_odoo_bin() {
  local candidates=( "/usr/bin/odoo" "/usr/local/bin/odoo" )
  local c
  for c in "${candidates[@]}"; do
    [[ -x "$c" ]] && { echo "$c"; return 0; }
  done
  command -v odoo &>/dev/null && command -v odoo || return 1
}

detect_bare_systemd() {
  local u
  for u in odoo odoo17 odoo-server; do
    if systemctl list-unit-files --type=service "$u.service" &>/dev/null 2>&1; then
      if systemctl is-enabled "$u.service" &>/dev/null 2>&1 || systemctl status "$u.service" &>/dev/null 2>&1; then
        echo "$u"
        return 0
      fi
    fi
  done
  return 1
}

print_discovery_summary() {
  echo ""
  echo -e "${CYAN}--- Valores descobertos ---${NC}"
  echo "  Modo:            ${INSTALL_MODE}"
  if [[ "$INSTALL_MODE" == "docker" ]]; then
    echo "  Compose:         ${COMPOSE_DIR}"
    echo "  Serviço web:     ${WEB_SVC}"
  fi
  echo "  Addons:          ${ADDONS_DIR}"
  echo "  Base de dados:   ${DB_NAME}"
  echo -e "${CYAN}---------------------------${NC}"
  echo ""
}

discover_installation() {
  COMPOSE_DIR=""
  WEB_SVC="${SHIPPING_HUB_WEB_SERVICE:-}"
  ADDONS_DIR="${SHIPPING_HUB_ADDONS_DIR:-}"
  DB_NAME="${SHIPPING_HUB_DB:-}"
  ODOO_CONTAINER_ID=""

  if [[ -n "${SHIPPING_HUB_INSTALL_MODE:-}" ]]; then
    INSTALL_MODE="$SHIPPING_HUB_INSTALL_MODE"
  elif [[ -n "${SHIPPING_HUB_COMPOSE_DIR:-}" ]]; then
    INSTALL_MODE="docker"
  elif docker_available && { [[ -n "$(list_running_odoo_containers | head -1)" ]] || find_all_compose_dirs | head -1 | grep -q .; }; then
    INSTALL_MODE="docker"
  elif detect_bare_odoo_bin &>/dev/null || detect_bare_systemd &>/dev/null; then
    INSTALL_MODE="bare"
  else
    INSTALL_MODE="docker"
  fi

  if [[ "$INSTALL_MODE" == "docker" ]]; then
    if [[ -n "${SHIPPING_HUB_COMPOSE_DIR:-}" ]]; then
      COMPOSE_DIR="$(cd "$SHIPPING_HUB_COMPOSE_DIR" && pwd)"
      WEB_SVC="${SHIPPING_HUB_WEB_SERVICE:-$(detect_web_service "$COMPOSE_DIR")}"
      ODOO_CONTAINER_ID="$( ( cd "$COMPOSE_DIR" && compose_cmd ps -q "$WEB_SVC" 2>/dev/null ) | head -1 )" || true
    else
      local picked=""
      picked="$(pick_compose_candidate || true)"
      if [[ -n "$picked" ]]; then
        IFS='|' read -r COMPOSE_DIR WEB_SVC ODOO_CONTAINER_ID _ <<< "$picked"
      fi
      if [[ -z "$COMPOSE_DIR" ]]; then
        if [[ "${SHIPPING_HUB_NONINTERACTIVE:-}" == "1" ]]; then
          COMPOSE_DIR="$HOME/odoo-dev"
        else
          COMPOSE_DIR="$(prompt_default SHIPPING_HUB_COMPOSE_DIR "Caminho da pasta com docker-compose.yml (descoberta falhou)" "$HOME/odoo-dev")"
        fi
        WEB_SVC="${SHIPPING_HUB_WEB_SERVICE:-$(detect_web_service "$COMPOSE_DIR")}"
        ODOO_CONTAINER_ID="$( ( cd "$COMPOSE_DIR" && compose_cmd ps -q "$WEB_SVC" 2>/dev/null ) | head -1 )" || true
      fi
    fi

    if [[ ! -f "$COMPOSE_DIR/docker-compose.yml" && ! -f "$COMPOSE_DIR/docker-compose.yaml" && ! -f "$COMPOSE_DIR/compose.yml" ]]; then
      log_err "docker-compose não encontrado em: $COMPOSE_DIR"
      return 1
    fi

    WEB_SVC="$(detect_web_service "$COMPOSE_DIR")"
    [[ -n "${SHIPPING_HUB_WEB_SERVICE:-}" ]] && WEB_SVC="$SHIPPING_HUB_WEB_SERVICE"
    if [[ "$WEB_SVC" == "db" ]]; then
      log_warn "Serviço web inválido (db); a usar serviço Odoo do compose."
      WEB_SVC="$(detect_web_service "$COMPOSE_DIR")"
    fi
    ODOO_CONTAINER_ID="$( ( cd "$COMPOSE_DIR" && compose_cmd ps -q "$WEB_SVC" 2>/dev/null ) | head -1 )" || true
    ADDONS_DIR="$(resolve_addons_dir "$COMPOSE_DIR" "$ODOO_CONTAINER_ID")"
    local db_svc
    db_svc="$(detect_db_service "$COMPOSE_DIR")"
    local web_cname=""
    [[ -n "$ODOO_CONTAINER_ID" ]] && web_cname="$(docker_cli inspect -f "{{.Name}}" "$ODOO_CONTAINER_ID" 2>/dev/null | sed "s|^/||")" || true
    DB_NAME="$(pick_database_name "$COMPOSE_DIR" "$db_svc" "$ODOO_CONTAINER_ID" "$web_cname")"
  else
    INSTALL_MODE="bare"
    if [[ -z "$ADDONS_DIR" ]]; then
      ADDONS_DIR="$(detect_bare_addons || true)"
    fi
    if [[ -z "$ADDONS_DIR" ]]; then
      ADDONS_DIR="$(prompt_default SHIPPING_HUB_ADDONS_DIR "Caminho para extra-addons no servidor" "/opt/odoo/extra-addons")"
    fi
    if [[ -z "$DB_NAME" ]]; then
      DB_NAME="$(prompt_default SHIPPING_HUB_DB "Nome da base de dados Odoo" "odoo")"
    fi
  fi

  return 0
}


copy_module() {
  local target_parent="$1"
  local dest="$target_parent/$MODULE_NAME"

  if [[ ! -d "$target_parent" ]]; then
    log_err "Pasta de addons não existe: $target_parent"
    return 1
  fi

  log_info "Origem:  $MODULE_DIR"
  log_info "Destino: $dest"

  if [[ "$INSTALL_CONFIRMED" != "1" ]]; then
    if [[ -d "$dest" ]]; then
      log_warn "Já existe instalação em $dest (será atualizada)."
      confirm "Continuar a copiar/sobrescrever o módulo?" || { log_err "Operação cancelada."; return 1; }
    else
      confirm "Confirmar cópia do módulo para $dest?" || { log_err "Operação cancelada."; return 1; }
    fi
  elif [[ -d "$dest" ]]; then
    log_warn "Já existe instalação em $dest (será atualizada)."
  fi

  mkdir -p "$dest"
  if command -v rsync &>/dev/null; then
    rsync -a --delete \
      --exclude '.git/' \
      --exclude '__pycache__/' \
      --exclude '*.pyc' \
      --exclude '.DS_Store' \
      --exclude '.i18n-venv/' \
      "$MODULE_DIR/" "$dest/"
  else
    rm -rf "$dest"
    mkdir -p "$dest"
    cp -a "$MODULE_DIR/." "$dest/"
    rm -rf "$dest/.git" "$dest/.i18n-venv" 2>/dev/null || true
    find "$dest" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$dest" -name '*.pyc' -delete 2>/dev/null || true
  fi
  log_info "Módulo copiado com sucesso."
}

docker_pip_install_cmd() {
  local req_in_container="/mnt/extra-addons/${MODULE_NAME}/requirements.txt"
  # Sem exit 0 intermédio: num bash "pip && odoo" um exit 0 após pip impede o odoo -u.
  cat <<EOF
pip() { command -v pip3 &>/dev/null && pip3 "\$@" || python3 -m pip "\$@"; }
pip install --user -r '${req_in_container}' || pip install -r '${req_in_container}' || true
python3 -c "import requests" || exit 1
python3 -c "import pypdf" 2>/dev/null || true
EOF
}

run_pip_in_odoo_container() {
  local compose_dir="$1"
  local web_svc="$2"
  local mode="${3:-run}"
  local pip_script
  pip_script="$(docker_pip_install_cmd)"

  if [[ "$mode" == "exec" ]]; then
    ( cd "$compose_dir" && compose_cmd exec -T "$web_svc" bash -lc "$pip_script" )
    return
  fi
  ( cd "$compose_dir" && compose_cmd run --rm --no-deps "$web_svc" bash -lc "$pip_script" ) \
    || ( cd "$compose_dir" && compose_cmd run --rm --no-deps --user root "$web_svc" \
      bash -lc "python3 -m pip install -r /mnt/extra-addons/${MODULE_NAME}/requirements.txt" )
}

install_python_deps_docker() {
  local compose_dir="$1"
  local web_svc="$2"
  local req="${ADDONS_DIR}/${MODULE_NAME}/requirements.txt"

  if [[ ! -f "$req" ]]; then
    log_warn "requirements.txt não encontrado em $req"
    return 0
  fi

  log_info "A instalar dependências Python (contentor efémero, igual ao odoo -u)..."
  if ! run_pip_in_odoo_container "$compose_dir" "$web_svc" run; then
    log_warn "pip no contentor efémero falhou; tentando no serviço web em execução..."
    run_pip_in_odoo_container "$compose_dir" "$web_svc" exec || \
      log_warn "Instale manualmente: cd \"$compose_dir\" && docker compose run --rm --no-deps $web_svc pip3 install -r /mnt/extra-addons/${MODULE_NAME}/requirements.txt"
  fi
}

install_python_deps_bare() {
  local req="${ADDONS_DIR}/${MODULE_NAME}/requirements.txt"
  [[ ! -f "$req" ]] && return 0

  local pip_cmd=""
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    pip_cmd="pip3"
  elif [[ -x "${SHIPPING_HUB_VENV:-}/bin/pip3" ]]; then
    pip_cmd="${SHIPPING_HUB_VENV}/bin/pip3"
  elif command -v pip3 &>/dev/null; then
    pip_cmd="pip3"
    log_warn "A usar pip3 do sistema; prefira o venv do Odoo se existir."
  fi

  if [[ -z "$pip_cmd" ]]; then
    log_warn "pip3 não encontrado. Instale manualmente: pip3 install -r $req"
    return 0
  fi
  if [[ "$INSTALL_CONFIRMED" == "1" ]] || confirm "Instalar dependências com $pip_cmd install -r requirements.txt?"; then
    "$pip_cmd" install -r "$req" || log_warn "Instalação pip falhou."
  else
    log_warn "Instalação pip cancelada."
  fi
}

verify_shipping_hub_schema_docker() {
  local compose_dir="$1"
  local db_name="$2"
  local db_svc="${SHIPPING_HUB_DB_SERVICE:-}"
  local pg_user="${SHIPPING_HUB_PGUSER:-odoo}"
  local column="shipping_hub_number_of_packages"
  local check_sql="SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='stock_picking' AND column_name='${column}' LIMIT 1;"

  [[ -z "$db_svc" ]] && db_svc="$(detect_db_service "$compose_dir")"

  log_info "A verificar esquema: stock_picking.${column} na base ${db_name}..."
  local result=""
  result="$( cd "$compose_dir" && compose_cmd exec -T "$db_svc" \
    psql -U "$pg_user" -d "$db_name" -tAc "$check_sql" 2>/dev/null | tr -d '[:space:]' )" || true

  if [[ "$result" == "1" ]]; then
    log_info "Esquema OK: coluna stock_picking.${column} presente."
    return 0
  fi

  log_err "Esquema em falta: stock_picking.${column} não existe na base ${db_name}."
  log_err "O módulo foi copiado mas a atualização Odoo (-u ${MODULE_NAME}) não aplicou as colunas."
  log_err "Execute: cd \"${compose_dir}\" && docker compose stop web && docker compose run --rm --no-deps web odoo -u ${MODULE_NAME} -d ${db_name} --stop-after-init && docker compose up -d"
  return 1
}

upgrade_module_docker() {
  local compose_dir="$1"
  local web_svc="$2"
  local db_name="$3"

  if [[ -z "$db_name" ]]; then
    log_err "Nome da base de dados em falta. Defina SHIPPING_HUB_DB ou garanta descoberta automática."
    return 1
  fi

  log_info "A parar serviço $web_svc (evita conflito com odoo -u)..."
  ( cd "$compose_dir" && compose_cmd stop "$web_svc" )

  log_info "A instalar dependências Python no contentor Odoo..."
  run_pip_in_odoo_container "$compose_dir" "$web_svc" run || true

  log_info "A atualizar módulo $MODULE_NAME na base $db_name (odoo -u --stop-after-init)..."
  if ! ( cd "$compose_dir" && compose_cmd run --rm --no-deps "$web_svc" \
    odoo -u "$MODULE_NAME" -d "$db_name" --stop-after-init ); then
    log_err "Falha ao atualizar o módulo. A repor serviços..."
    ( cd "$compose_dir" && compose_cmd up -d )
    return 1
  fi

  log_info "Atualização Odoo concluída; a iniciar serviços..."
  ( cd "$compose_dir" && compose_cmd up -d )
  run_pip_in_odoo_container "$compose_dir" "$web_svc" exec || true
  ( cd "$compose_dir" && compose_cmd restart "$web_svc" ) || true

  if ! verify_shipping_hub_schema_docker "$compose_dir" "$db_name"; then
    log_warn "A repetir odoo -u (coluna em falta após primeira tentativa)..."
    ( cd "$compose_dir" && compose_cmd run --rm --no-deps "$web_svc" \
      odoo -u "$MODULE_NAME" -d "$db_name" --stop-after-init ) || true
    ( cd "$compose_dir" && compose_cmd up -d )
    verify_shipping_hub_schema_docker "$compose_dir" "$db_name"
  fi
}

upgrade_module_bare() {
  local db_name="$1"
  local odoo_bin="${SHIPPING_HUB_ODOO_BIN:-}"

  if [[ -z "$odoo_bin" ]]; then
    odoo_bin="$(detect_bare_odoo_bin || true)"
  fi
  if [[ -z "$odoo_bin" ]]; then
    odoo_bin="$(prompt_default SHIPPING_HUB_ODOO_BIN "Caminho para o binário odoo" "/usr/bin/odoo")"
  fi

  if [[ ! -x "$odoo_bin" && ! -f "$odoo_bin" ]]; then
    log_warn "Binário Odoo não encontrado: $odoo_bin"
    confirm "Continuar sem executar odoo -u (atualize manualmente nas Apps)?" || return 1
    return 0
  fi

  log_info "A executar: $odoo_bin -u $MODULE_NAME -d $db_name --stop-after-init"
  if [[ "$INSTALL_CONFIRMED" != "1" ]]; then
    confirm "Executar atualização do módulo agora?" || { log_warn "Atualização Odoo ignorada."; return 0; }
  fi

  "$odoo_bin" -u "$MODULE_NAME" -d "$db_name" --stop-after-init --addons-path="${ADDONS_DIR}" || {
    log_err "Falha ao executar odoo -u."
    return 1
  }
}

restart_bare() {
  local unit="${SHIPPING_HUB_SYSTEMD:-}"
  if [[ -z "$unit" ]]; then
    unit="$(detect_bare_systemd || true)"
  fi
  [[ -z "$unit" ]] && { log_warn "Reinicie o Odoo manualmente."; return 0; }
  if [[ "$INSTALL_CONFIRMED" == "1" ]] || confirm "Reiniciar systemctl $unit?"; then
    sudo systemctl restart "$unit" && log_info "Serviço $unit reiniciado." || log_err "Falha ao reiniciar $unit."
  fi
}


configure_odoo_hub_gateway() {
  local db_name="${1:-}"
  [[ -z "${SHIPPING_HUB_API_TOKEN:-}" ]] && return 0
  [[ -z "${SHIPPING_HUB_GATEWAY_URL:-}" ]] && SHIPPING_HUB_GATEWAY_URL="https://stip.pt/hub-test"
  local skip="${SHIPPING_HUB_SKIP_IAP_CHARGE:-True}"
  local env_name="${SHIPPING_HUB_ENVIRONMENT:-sandbox}"
  local py_code
  py_code=$(cat <<PYCODE
token = '${SHIPPING_HUB_API_TOKEN}'
url = '${SHIPPING_HUB_GATEWAY_URL}'
hub_env = '${env_name}'
skip = '${skip}'
icp = env['ir.config_parameter'].sudo()
icp.set_param('shipping_hub_connector.gateway_base_url', url)
icp.set_param('shipping_hub_connector.api_token', token)
icp.set_param('shipping_hub_connector.environment', hub_env)
icp.set_param('shipping_hub_connector.skip_iap_charge', skip)
print('Shipping Hub ir.config_parameter updated')
PYCODE
)
  if [[ "$INSTALL_MODE" == "docker" && -n "${COMPOSE_DIR:-}" ]]; then
    compose_cmd "$COMPOSE_DIR" exec -T "${WEB_SVC:-web}" odoo shell -d "$db_name" --no-http <<< "$py_code" && \
      log_info "Gateway URL/token gravados em ir.config_parameter." || \
      log_warn "Não foi possível gravar settings Odoo automaticamente."
  elif [[ -n "${SHIPPING_HUB_ODOO_BIN:-}" ]]; then
    "$SHIPPING_HUB_ODOO_BIN" shell -d "$db_name" --no-http <<< "$py_code" && \
      log_info "Gateway URL/token gravados." || log_warn "Falha ao gravar settings Odoo."
  fi
}

print_summary() {
  local ok="$1"
  echo ""
  echo "=========================================="
  if [[ "$ok" == "1" ]]; then
    echo -e "${GREEN}Instalação concluída com sucesso.${NC}"
    echo "Módulo: $MODULE_NAME"
    echo "Addons: ${ADDONS_DIR:-—}"
    echo "Modo:   ${INSTALL_MODE:-—}"
    [[ -n "${DB_NAME:-}" ]] && echo "Base:   $DB_NAME"
    echo ""
    echo "Verifique no Odoo: Apps → atualizar lista → Shipping Hub Connector."
    echo "Gateway (testes): https://stip.pt/hub-test — ver docs/AMBIENTE_TESTES_HETZNER.md"
    [[ -n "${SHIPPING_HUB_GATEWAY_URL:-}" ]] && echo "Gateway URL: $SHIPPING_HUB_GATEWAY_URL"

  else
    echo -e "${RED}Instalação concluída com erros.${NC}"
    echo "Revise as mensagens acima e complete passos manuais se necessário."
  fi
  echo "=========================================="
}

main() {
  echo ""
  log_info "Instalador Shipping Hub Connector (Linux)"
  log_info "Pasta do módulo: $MODULE_DIR"
  echo ""

  if ! init_docker_cli; then
    log_warn "Docker não acessível sem elevação (grupo docker ou sudo)."
    if [[ "$(id -u)" -ne 0 ]]; then
      log_warn "Tente: sudo $0"
    fi
  fi

  FAILED=0
  INSTALL_MODE=""

  if ! discover_installation; then
    print_summary 0
    exit 1
  fi

  print_discovery_summary

  if confirm_yes_default "Confirma instalação com estes valores?"; then
    INSTALL_CONFIRMED=1
  else
    log_err "Instalação cancelada pelo utilizador."
    exit 1
  fi

  if [[ "$INSTALL_MODE" == "docker" ]]; then
    copy_module "$ADDONS_DIR" || FAILED=1
    if [[ $FAILED -eq 0 ]]; then
      install_python_deps_docker "$COMPOSE_DIR" "$WEB_SVC" || true
      upgrade_module_docker "$COMPOSE_DIR" "$WEB_SVC" "$DB_NAME" || FAILED=1
    fi
  else
    copy_module "$ADDONS_DIR" || FAILED=1
    if [[ $FAILED -eq 0 ]]; then
      install_python_deps_bare || true
      upgrade_module_bare "$DB_NAME" || FAILED=1
      restart_bare || true
    fi
  fi

  if [[ $FAILED -eq 0 ]]; then
    configure_odoo_hub_gateway "$DB_NAME"
    print_summary 1
    exit 0
  else
    print_summary 0
    exit 1
  fi
}

main "$@"
