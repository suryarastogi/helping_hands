#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RUNTIME_DIR="${REPO_ROOT}/runs/local-stack"
PID_DIR="${RUNTIME_DIR}/pids"
LOG_DIR="${RUNTIME_DIR}/logs"

SERVER_APP="helping_hands.server.app:app"
CELERY_APP="helping_hands.server.celery_app:celery_app"

usage() {
  cat <<'EOF'
Usage: scripts/run-local-stack.sh <command> [service]

Commands:
  start      Start server, worker, beat, and flower in the background.
  stop       Stop all running services from this script.
  restart    Restart all services.
  status     Show current service status.
  logs       Tail logs for all services or a specific service.

Services:
  server | worker | beat | flower

Examples:
  scripts/run-local-stack.sh start
  scripts/run-local-stack.sh status
  scripts/run-local-stack.sh logs worker
EOF
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

ensure_runtime_dirs() {
  mkdir -p "${PID_DIR}" "${LOG_DIR}"
}

load_env() {
  local env_file="${REPO_ROOT}/.env"
  local line key value
  if [[ ! -f "${env_file}" ]]; then
    return 0
  fi

  while IFS= read -r line || [[ -n "${line}" ]]; do
    # Trim leading whitespace.
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    [[ "${line}" != *"="* ]] && continue

    key="${line%%=*}"
    value="${line#*=}"

    # Support optional `export KEY=...`.
    key="${key#export }"
    # Trim whitespace around key.
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"

    # Trim whitespace around value.
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    if [[ "${value}" =~ ^\"(.*)\"$ ]]; then
      value="${BASH_REMATCH[1]}"
    elif [[ "${value}" =~ ^\'(.*)\'$ ]]; then
      value="${BASH_REMATCH[1]}"
    fi

    if [[ "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      export "${key}=${value}"
    fi
  done <"${env_file}"
}

set_defaults() {
  : "${SERVER_PORT:=8000}"
  : "${FLOWER_PORT:=5555}"
  : "${REDIS_URL:=redis://localhost:6379/0}"
  : "${CELERY_BROKER_URL:=${REDIS_URL}}"
  : "${CELERY_RESULT_BACKEND:=redis://localhost:6379/1}"

  export SERVER_PORT
  export FLOWER_PORT
  export REDIS_URL
  export CELERY_BROKER_URL
  export CELERY_RESULT_BACKEND
  export PYTHONUNBUFFERED=1
}

normalize_redis_url_for_local() {
  local value="$1"
  if [[ "${value}" =~ ^redis://redis([:/]|$) ]]; then
    echo "redis://localhost${value#redis://redis}"
    return 0
  fi
  echo "${value}"
}

adjust_docker_redis_hosts_for_local() {
  if [[ "${HH_LOCAL_STACK_KEEP_DOCKER_HOSTS:-0}" == "1" ]]; then
    return 0
  fi

  local before after

  before="${REDIS_URL}"
  after="$(normalize_redis_url_for_local "${before}")"
  if [[ "${before}" != "${after}" ]]; then
    REDIS_URL="${after}"
    echo "Adjusted REDIS_URL for local run: ${before} -> ${after}"
  fi

  before="${CELERY_BROKER_URL}"
  after="$(normalize_redis_url_for_local "${before}")"
  if [[ "${before}" != "${after}" ]]; then
    CELERY_BROKER_URL="${after}"
    echo "Adjusted CELERY_BROKER_URL for local run: ${before} -> ${after}"
  fi

  before="${CELERY_RESULT_BACKEND}"
  after="$(normalize_redis_url_for_local "${before}")"
  if [[ "${before}" != "${after}" ]]; then
    CELERY_RESULT_BACKEND="${after}"
    echo "Adjusted CELERY_RESULT_BACKEND for local run: ${before} -> ${after}"
  fi

  export REDIS_URL
  export CELERY_BROKER_URL
  export CELERY_RESULT_BACKEND
}

pid_file_for() {
  local name="$1"
  echo "${PID_DIR}/${name}.pid"
}

log_file_for() {
  local name="$1"
  echo "${LOG_DIR}/${name}.log"
}

is_pid_running() {
  local pid="$1"
  kill -0 "${pid}" >/dev/null 2>&1
}

start_service() {
  local name="$1"
  shift

  local pid_file log_file existing_pid new_pid
  pid_file="$(pid_file_for "${name}")"
  log_file="$(log_file_for "${name}")"

  if [[ -f "${pid_file}" ]]; then
    existing_pid="$(cat "${pid_file}")"
    if is_pid_running "${existing_pid}"; then
      echo "${name}: already running (pid ${existing_pid})"
      return 0
    fi
    rm -f "${pid_file}"
  fi

  (
    cd "${REPO_ROOT}"
    nohup "$@" >"${log_file}" 2>&1 &
    echo $! >"${pid_file}"
  )

  new_pid="$(cat "${pid_file}")"
  sleep 0.3
  if is_pid_running "${new_pid}"; then
    echo "${name}: started (pid ${new_pid})"
  else
    echo "${name}: failed to start (see ${log_file})" >&2
    return 1
  fi
}

stop_service() {
  local name="$1"
  local pid_file pid
  pid_file="$(pid_file_for "${name}")"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: not running"
    return 0
  fi

  pid="$(cat "${pid_file}")"
  if ! is_pid_running "${pid}"; then
    rm -f "${pid_file}"
    echo "${name}: stale pid file removed"
    return 0
  fi

  kill "${pid}" >/dev/null 2>&1 || true
  for _ in {1..20}; do
    if ! is_pid_running "${pid}"; then
      rm -f "${pid_file}"
      echo "${name}: stopped"
      return 0
    fi
    sleep 0.25
  done

  kill -9 "${pid}" >/dev/null 2>&1 || true
  rm -f "${pid_file}"
  echo "${name}: force stopped"
}

status_service() {
  local name="$1"
  local pid_file pid
  pid_file="$(pid_file_for "${name}")"
  if [[ ! -f "${pid_file}" ]]; then
    echo "${name}: not running"
    return 0
  fi

  pid="$(cat "${pid_file}")"
  if is_pid_running "${pid}"; then
    echo "${name}: running (pid ${pid})"
  else
    echo "${name}: not running (stale pid ${pid})"
  fi
}

start_all() {
  require_command uv
  ensure_runtime_dirs
  load_env
  set_defaults
  adjust_docker_redis_hosts_for_local

  echo "Using Celery broker: ${CELERY_BROKER_URL}"
  echo "Using Celery result backend: ${CELERY_RESULT_BACKEND}"
  echo "Server port: ${SERVER_PORT}, Flower port: ${FLOWER_PORT}"

  start_service \
    "server" \
    uv run --extra server uvicorn "${SERVER_APP}" --host 0.0.0.0 --port "${SERVER_PORT}"

  start_service \
    "worker" \
    uv run --extra server celery -A "${CELERY_APP}" worker --pool=threads --concurrency=4 --loglevel=info

  start_service \
    "beat" \
    uv run --extra server celery -A "${CELERY_APP}" beat --loglevel=info

  start_service \
    "flower" \
    uv run --extra server celery -A "${CELERY_APP}" flower --port="${FLOWER_PORT}"

  echo
  echo "Logs: ${LOG_DIR}"
  echo "Use './scripts/run-local-stack.sh logs' to tail all logs."
}

stop_all() {
  ensure_runtime_dirs
  stop_service flower
  stop_service beat
  stop_service worker
  stop_service server
}

status_all() {
  ensure_runtime_dirs
  status_service server
  status_service worker
  status_service beat
  status_service flower
}

tail_logs() {
  ensure_runtime_dirs
  local target="${1:-all}"

  case "${target}" in
    all)
      tail -n 100 -f \
        "$(log_file_for server)" \
        "$(log_file_for worker)" \
        "$(log_file_for beat)" \
        "$(log_file_for flower)"
      ;;
    server | worker | beat | flower)
      tail -n 100 -f "$(log_file_for "${target}")"
      ;;
    *)
      echo "Unknown service '${target}'. Expected server|worker|beat|flower." >&2
      exit 1
      ;;
  esac
}

main() {
  local command="${1:-}"
  local service="${2:-}"

  case "${command}" in
    start)
      start_all
      ;;
    stop)
      stop_all
      ;;
    restart)
      stop_all
      start_all
      ;;
    status)
      status_all
      ;;
    logs)
      tail_logs "${service}"
      ;;
    "" | -h | --help | help)
      usage
      ;;
    *)
      echo "Unknown command '${command}'." >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
