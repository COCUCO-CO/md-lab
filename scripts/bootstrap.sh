#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
ENV_PREFIX="$ROOT/.venv/conda"
mkdir -p "$TOOLS" "$ROOT/.venv"

if command -v micromamba >/dev/null 2>&1; then
  MAMBA="$(command -v micromamba)"
elif [[ -x "$TOOLS/micromamba" ]]; then
  MAMBA="$TOOLS/micromamba"
else
  echo "Installing micromamba locally under .tools/"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "$tmp" bin/micromamba
  mv "$tmp/bin/micromamba" "$TOOLS/micromamba"
  chmod +x "$TOOLS/micromamba"
  MAMBA="$TOOLS/micromamba"
fi

if [[ -d "$ENV_PREFIX" ]]; then
  echo "Environment already exists: $ENV_PREFIX"
  "$MAMBA" env update -y -p "$ENV_PREFIX" -f "$ROOT/environment.yml"
else
  "$MAMBA" create -y -p "$ENV_PREFIX" -f "$ROOT/environment.yml"
fi

"$MAMBA" run -p "$ENV_PREFIX" python -m pip check
"$MAMBA" run -p "$ENV_PREFIX" python -m openmm.testInstallation
"$MAMBA" env export -p "$ENV_PREFIX" --explicit > "$ROOT/state/environment-explicit.txt"
"$MAMBA" env export -p "$ENV_PREFIX" > "$ROOT/state/environment-solved.yml"

cat <<MSG
Bootstrap complete.
Activate with:
  eval "\$($MAMBA shell hook -s bash)"
  micromamba activate "$ENV_PREFIX"
Or run commands through:
  $MAMBA run -p "$ENV_PREFIX" <command>
MSG
