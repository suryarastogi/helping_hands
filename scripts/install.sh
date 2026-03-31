#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# helping_hands interactive installer
#
# Detects the user's environment and walks them through the appropriate
# installation path:
#   1. API-only  — user only needs the server/API (no CLI usage)
#   2. CLI (existing) — user already has a working CLI environment
#   3. CLI (fresh)    — full setup from scratch
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_URL="https://github.com/suryarastogi/helping_hands.git"
BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No colour

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { echo -e "${BLUE}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[  ok]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
fail()  { echo -e "${RED}[fail]${NC}  $*"; }
step()  { echo -e "\n${BOLD}${CYAN}▸ $*${NC}"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

prompt_yes_no() {
  local prompt="$1"
  local default="${2:-y}"
  local yn
  if [[ "$default" == "y" ]]; then
    read -r -p "$(echo -e "${prompt} ${DIM}[Y/n]${NC} ")" yn
    yn="${yn:-y}"
  else
    read -r -p "$(echo -e "${prompt} ${DIM}[y/N]${NC} ")" yn
    yn="${yn:-n}"
  fi
  [[ "$yn" =~ ^[Yy] ]]
}

# ---------------------------------------------------------------------------
# Detect environment
# ---------------------------------------------------------------------------

detect_environment() {
  step "Detecting environment"

  HAS_PYTHON=false
  HAS_UV=false
  HAS_GIT=false
  HAS_DOCKER=false
  PYTHON_CMD=""
  PYTHON_VERSION=""
  IN_REPO=false

  # Python
  for cmd in python3 python; do
    if has_cmd "$cmd"; then
      local ver
      ver="$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)"
      local major minor
      major="${ver%%.*}"
      minor="${ver##*.}"
      if [[ "$major" -ge 3 && "$minor" -ge 12 ]]; then
        HAS_PYTHON=true
        PYTHON_CMD="$cmd"
        PYTHON_VERSION="$ver"
        break
      fi
    fi
  done

  # uv
  has_cmd uv && HAS_UV=true
  # git
  has_cmd git && HAS_GIT=true
  # docker
  has_cmd docker && HAS_DOCKER=true

  # Are we inside the repo already?
  if [[ -f "pyproject.toml" ]] && grep -q "helping.hands" pyproject.toml 2>/dev/null; then
    IN_REPO=true
  fi

  [[ "$HAS_PYTHON" == true ]] && ok "Python $PYTHON_VERSION ($PYTHON_CMD)" || warn "Python 3.12+ not found"
  [[ "$HAS_UV" == true ]]     && ok "uv found"     || warn "uv not found"
  [[ "$HAS_GIT" == true ]]    && ok "git found"     || warn "git not found"
  [[ "$HAS_DOCKER" == true ]] && ok "Docker found"  || info "Docker not found (optional)"
  [[ "$IN_REPO" == true ]]    && ok "Inside helping_hands repo" || info "Not inside the repo"
}

# ---------------------------------------------------------------------------
# Choose install path
# ---------------------------------------------------------------------------

choose_install_path() {
  step "Choose your setup"
  echo ""
  echo -e "  ${BOLD}1)${NC} API only      — Run the server; interact via HTTP/WebSocket (no CLI needed)"
  echo -e "  ${BOLD}2)${NC} CLI (update)  — You already have Python/uv/git; just install helping_hands"
  echo -e "  ${BOLD}3)${NC} CLI (fresh)   — Full setup from scratch (installs prerequisites + helping_hands)"
  echo ""
  local choice
  read -r -p "$(echo -e "Enter ${BOLD}1${NC}, ${BOLD}2${NC}, or ${BOLD}3${NC}: ")" choice

  case "$choice" in
    1) install_api_only ;;
    2) install_cli_existing ;;
    3) install_cli_fresh ;;
    *) fail "Invalid choice. Please re-run and pick 1, 2, or 3."; exit 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# Path 1: API-only (Docker or local server)
# ---------------------------------------------------------------------------

install_api_only() {
  step "API-only setup"

  if [[ "$IN_REPO" != true ]]; then
    clone_repo
  fi

  if [[ "$HAS_DOCKER" == true ]] && prompt_yes_no "Use Docker Compose? (recommended for API-only)"; then
    info "Starting with Docker Compose..."
    docker compose up --build -d
    echo ""
    ok "Server is running!"
    echo -e "  API:       ${CYAN}http://localhost:8000${NC}"
    echo -e "  Docs:      ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Frontend:  ${CYAN}http://localhost:5173${NC}"
  else
    info "Setting up local server..."
    install_uv_if_missing
    ensure_python
    info "Installing dependencies..."
    uv sync --extra server --extra github --extra langchain --extra atomic
    echo ""
    ok "Dependencies installed!"
    echo -e "\n  Start the stack with:"
    echo -e "    ${DIM}./scripts/run-local-stack.sh start${NC}"
    echo -e "\n  Or start manually:"
    echo -e "    ${DIM}uv run uvicorn helping_hands.server.app:app --reload${NC}"
  fi

  setup_env_file
  print_api_quickstart
}

# ---------------------------------------------------------------------------
# Path 2: CLI — prerequisites already installed
# ---------------------------------------------------------------------------

install_cli_existing() {
  step "CLI setup (existing environment)"

  # Verify prerequisites
  if [[ "$HAS_PYTHON" != true ]]; then
    fail "Python 3.12+ is required. Run option 3 (fresh install) instead."
    exit 1
  fi
  if [[ "$HAS_GIT" != true ]]; then
    fail "git is required. Install it and re-run."
    exit 1
  fi

  if [[ "$IN_REPO" != true ]]; then
    clone_repo
  fi

  install_uv_if_missing

  info "Installing helping_hands..."
  uv sync --dev

  if prompt_yes_no "Install optional extras (LangGraph, Atomic Agents, server)?"; then
    uv sync --extra langchain --extra atomic --extra server --extra github --extra mcp
    ok "All extras installed"
  fi

  info "Installing pre-commit hooks..."
  uv run pre-commit install || warn "pre-commit install failed (non-critical)"

  setup_env_file

  info "Running doctor check..."
  uv run helping-hands doctor || true

  print_cli_quickstart
}

# ---------------------------------------------------------------------------
# Path 3: CLI — fresh environment
# ---------------------------------------------------------------------------

install_cli_fresh() {
  step "CLI setup (fresh environment)"

  # --- git ---
  if [[ "$HAS_GIT" != true ]]; then
    step "Installing git"
    if has_cmd apt-get; then
      sudo apt-get update -qq && sudo apt-get install -y -qq git
    elif has_cmd brew; then
      brew install git
    elif has_cmd dnf; then
      sudo dnf install -y git
    elif has_cmd pacman; then
      sudo pacman -S --noconfirm git
    else
      fail "Cannot auto-install git. Please install it manually and re-run."
      exit 1
    fi
    ok "git installed"
  fi

  # --- Python 3.12+ ---
  if [[ "$HAS_PYTHON" != true ]]; then
    step "Installing Python 3.12+"
    if has_cmd apt-get; then
      sudo apt-get update -qq
      sudo apt-get install -y -qq software-properties-common
      sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
      sudo apt-get update -qq
      sudo apt-get install -y -qq python3.12 python3.12-venv python3.12-dev
      PYTHON_CMD="python3.12"
    elif has_cmd brew; then
      brew install python@3.12
      PYTHON_CMD="python3.12"
    elif has_cmd dnf; then
      sudo dnf install -y python3.12
      PYTHON_CMD="python3.12"
    else
      fail "Cannot auto-install Python 3.12+. Please install it manually and re-run."
      echo -e "  Visit: ${CYAN}https://www.python.org/downloads/${NC}"
      exit 1
    fi
    ok "Python installed ($PYTHON_CMD)"
    HAS_PYTHON=true
  fi

  # --- uv ---
  install_uv_if_missing

  # --- Clone & install ---
  if [[ "$IN_REPO" != true ]]; then
    clone_repo
  fi

  info "Installing helping_hands and all extras..."
  uv sync --dev
  uv sync --extra langchain --extra atomic --extra server --extra github --extra mcp

  info "Installing pre-commit hooks..."
  uv run pre-commit install || warn "pre-commit install failed (non-critical)"

  setup_env_file

  info "Running doctor check..."
  uv run helping-hands doctor || true

  print_cli_quickstart
}

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

clone_repo() {
  step "Cloning helping_hands"
  local target="${1:-helping_hands}"
  if [[ -d "$target" ]]; then
    info "Directory '$target' already exists — using it."
  else
    git clone "$REPO_URL" "$target"
  fi
  cd "$target"
  IN_REPO=true
  ok "Cloned to $(pwd)"
}

install_uv_if_missing() {
  if [[ "$HAS_UV" == true ]]; then return; fi
  step "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck source=/dev/null
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
  if has_cmd uv; then
    HAS_UV=true
    ok "uv installed"
  else
    fail "uv installation failed. Install manually: https://docs.astral.sh/uv/"
    exit 1
  fi
}

ensure_python() {
  if [[ "$HAS_PYTHON" != true ]]; then
    fail "Python 3.12+ is required."
    exit 1
  fi
}

setup_env_file() {
  if [[ -f ".env" ]]; then
    ok ".env file already exists"
    return
  fi

  step "Environment configuration"
  echo -e "  Set at least one AI provider API key to get started.\n"

  local env_lines=()

  read -r -p "  OPENAI_API_KEY (or press Enter to skip): " openai_key
  [[ -n "$openai_key" ]] && env_lines+=("OPENAI_API_KEY=$openai_key")

  read -r -p "  ANTHROPIC_API_KEY (or press Enter to skip): " anthropic_key
  [[ -n "$anthropic_key" ]] && env_lines+=("ANTHROPIC_API_KEY=$anthropic_key")

  read -r -p "  GOOGLE_API_KEY (or press Enter to skip): " google_key
  [[ -n "$google_key" ]] && env_lines+=("GOOGLE_API_KEY=$google_key")

  read -r -p "  GITHUB_TOKEN (or press Enter to skip): " github_token
  [[ -n "$github_token" ]] && env_lines+=("GITHUB_TOKEN=$github_token")

  if [[ ${#env_lines[@]} -gt 0 ]]; then
    printf '%s\n' "${env_lines[@]}" > .env
    ok "Created .env with ${#env_lines[@]} key(s)"
  else
    warn "No keys provided — create a .env file later with your API keys."
  fi
}

print_api_quickstart() {
  echo ""
  echo -e "${BOLD}${GREEN}Setup complete!${NC}"
  echo ""
  echo -e "  ${BOLD}Quick start (API):${NC}"
  echo -e "    ${DIM}# Submit a task via the API${NC}"
  echo -e "    curl -X POST http://localhost:8000/build \\"
  echo -e "      -H 'Content-Type: application/json' \\"
  echo -e "      -d '{\"repo_path\": \"owner/repo\", \"prompt\": \"Add tests\"}'"
  echo ""
  echo -e "    ${DIM}# Or open the web UI${NC}"
  echo -e "    open http://localhost:5173"
  echo ""
}

print_cli_quickstart() {
  echo ""
  echo -e "${BOLD}${GREEN}Setup complete!${NC}"
  echo ""
  echo -e "  ${BOLD}Quick start (CLI):${NC}"
  echo -e "    ${DIM}# Check your environment${NC}"
  echo -e "    uv run helping-hands doctor"
  echo ""
  echo -e "    ${DIM}# Run your first task${NC}"
  echo -e "    uv run helping-hands owner/repo --prompt \"Add a README\" --backend basic-langgraph"
  echo ""
  echo -e "    ${DIM}# Try the example${NC}"
  echo -e "    cd examples/fix-greeting && bash run.sh"
  echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  echo -e "\n${BOLD}${CYAN}helping_hands installer${NC}\n"
  detect_environment
  choose_install_path
}

main "$@"
