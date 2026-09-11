#!/usr/bin/env bash
# Stage 6 demo — automated test, diagnostics & release gate.
# Installs with uv, starts the virtual ECUs, runs the Robot Framework suites for real,
# runs a UDS DTC session, and renders a release-gate scorecard. Artifacts -> demo/out/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/demo/out"
cd "$ROOT"
mkdir -p "$OUT"
export PATH="$HOME/.local/bin:$PATH"

B=$'\033[1m'; G=$'\033[92m'; Y=$'\033[93m'; N=$'\033[0m'
step() { echo; echo "${B}${Y}==> $*${N}"; }

step "1/6  Install (uv sync + editable package)"
uv sync --extra dev --extra demo -q
uv pip install -q -e .

step "2/6  Start virtual ECUs (FastAPI BMS :8000 + Body Domain Controller)"
uv run vhil-start stop >/dev/null 2>&1 || true
uv run vhil-start start
for _ in $(seq 1 30); do curl -sf localhost:8000/health >/dev/null && break; sleep 0.5; done
echo "BMS health: $(curl -s localhost:8000/health)"
echo "BMS status: $(curl -s localhost:8000/ecu/status | cut -c1-160)..."
trap 'uv run vhil-start stop >/dev/null 2>&1 || true' EXIT

step "3/6  Robot Framework regression (tests/functional, 4 suites)"
ROBOT_RC=0
uv run robot --outputdir "$OUT" --name "Virtual HIL Release Gate" \
  --loglevel INFO --consolecolors on tests/ || ROBOT_RC=$?

step "4/6  pytest unit tests"
PYTEST_ARGS=()
if uv run pytest --collect-only -q tests/ 2>/dev/null | grep -q '::'; then
  uv run pytest tests/ -q --junitxml="$OUT/pytest.xml" || true
  PYTEST_ARGS=(--pytest "$OUT/pytest.xml")
else
  echo "no pytest unit tests present in tests/ (Robot suites are the regression)"
fi

step "5/6  UDS (ISO 14229) diagnostic session: inject fault -> read DTC -> clear -> read"
UDS_RC=0
uv run python demo/uds_dtc_session.py || UDS_RC=$?

step "6/6  Release-gate scorecard"
GATE_RC=0
uv run python demo/scorecard.py "$OUT/output.xml" "$OUT/release_gate_scorecard.png" \
  "${PYTEST_ARGS[@]}" --uds "$OUT/uds_session.txt" || GATE_RC=$?

echo
echo "${B}Artifacts in demo/out/:${N}"
ls -1 "$OUT"
echo
echo "Open in a browser:  $OUT/report.html   $OUT/log.html"
if [ "$GATE_RC" -eq 0 ] && [ "$ROBOT_RC" -eq 0 ] && [ "$UDS_RC" -eq 0 ]; then
  echo "${B}${G}RELEASE GATE: PASS — software is cleared to ship.${N}"
else
  echo "${B}RELEASE GATE: BLOCKED (robot=$ROBOT_RC uds=$UDS_RC)${N}"
  exit 1
fi
