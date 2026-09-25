#!/usr/bin/env bash
# The clean-slate end-to-end validation run on the GCP e2-standard-4 VM (CHECKS.md section 7).
# Purges every Docker image and layer first, so the 3 GB recording is re-downloaded and both
# images rebuild from nothing, then runs the static checks, the oracle and nop.
# Log of the actual run: docs/runs/final-e2e-test/final_test.log
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd ~/work/TerminalBench
LOG=~/work/final_test.log; : > "$LOG"
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== 0. clean slate ==="
docker rm -f $(docker ps -aq) 2>/dev/null | tail -1
docker system prune -af --volumes >/dev/null 2>&1
say "images after prune: $(docker images -q | wc -l); disk free: $(df -h / | tail -1 | awk '{print $4}')"

say "=== 1. static checks (22) ==="
p=0; f=0
for c in ~/work/tb3/scripts/checks/check-*.sh; do
  if bash "$c" tasks/aircraft-orbit-mapping >/dev/null 2>&1; then p=$((p+1)); else f=$((f+1)); say "  FAIL $(basename "$c")"; fi
done
say "static checks: $p pass / $f fail"

say "=== 2. oracle validation (harbor, docker backend, from-scratch build) ==="
harbor run -p tasks/aircraft-orbit-mapping --agent oracle --env docker -o ~/work/jobs --job-name final-oracle >> "$LOG" 2>&1
O=$(cat ~/work/jobs/final-oracle/*/verifier/reward.txt 2>/dev/null || echo "?")
say "oracle reward: $O"

say "=== 3. nop validation ==="
harbor run -p tasks/aircraft-orbit-mapping --agent nop --env docker -o ~/work/jobs --job-name final-nop >> "$LOG" 2>&1
N=$(cat ~/work/jobs/final-nop/*/verifier/reward.txt 2>/dev/null || echo "?")
say "nop reward: $N"

say "=== RESULT: static $p/$((p+f)) | oracle $O (want 1) | nop $N (want 0) ==="
