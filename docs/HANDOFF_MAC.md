# Handoff — continuing on the Mac

State as of 2026-09-16 (Linux dev box, disk full). Everything needed is in this repo
(https://github.com/SIDDARTHAREDDY8/TerminalBench) plus the public dataset
https://huggingface.co/datasets/pinkman9/aircraft-orbit-mapping (orbit.mcap, 2.92 GB).

## Done
- Task scaffold `tasks/aircraft-orbit-mapping/` complete: environment (ros:humble base,
  downloads the bag by URL + SHA-256), oracle solution (lidarslam_ros2 tarball + launch +
  compose_trajectory.py + extract_aircraft.py + solve.sh), separate verifier (pytest + CTRF,
  reference model + 100 cropped keyframes baked into tests/), task.toml, README skeleton.
- 22/22 TB3 static checks pass locally. Verifier unit tests 27/27.
- Calibration (native lidarslam runs, see scratch/calibrate/CALIBRATION.md — copied below):
  oracle 5/5 pass (reacc 0.80/0.996, model 0.78/0.99, apron 1.6 %); GNSS-INS shortcut 0.68/0.59
  → fails; nop fails. Thresholds P=0.72, C=0.90, junk ≤ 0.30, apron ≤ 2 %.
- Fact sheet for the hand-written instruction: docs/instruction_facts.md.

## Mac setup (one time)
```
git clone git@github.com:SIDDARTHAREDDY8/TerminalBench.git && cd TerminalBench
# Docker Desktop running (allocate ≥ 8 CPU / 16 GB RAM / 80 GB disk in settings)
curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install harbor
npm i -g @openai/codex && codex login
claude setup-token          # → CLAUDE_CODE_OAUTH_TOKEN
gh auth login
git clone --depth 1 https://github.com/harbor-framework/terminal-bench-3 ../tb3   # CI checks + prompts
```
Note: the environment image is linux/amd64 (ROS 2 Humble apt); on Apple Silicon Docker runs it
under emulation — works, slower. Set `DOCKER_DEFAULT_PLATFORM=linux/amd64` for harbor runs.

## Next steps, in order
1. Static checks: `for c in ../tb3/scripts/checks/check-*.sh; do bash "$c" tasks/aircraft-orbit-mapping; done`
2. Build both images once by hand to shake out apt/pip issues:
   `docker build -t aom-env tasks/aircraft-orbit-mapping/environment` and
   `docker build -t aom-tests tasks/aircraft-orbit-mapping/tests`
3. Oracle + nop through harbor (exact CI form):
   `harbor run -p tasks/aircraft-orbit-mapping --agent oracle --env docker -o jobs`
   `harbor run -p tasks/aircraft-orbit-mapping --agent nop --env docker -o jobs`
   Expect oracle reward 1.0 (solve.sh: colcon build ~10 min + bag play ~5 min at 0.5x + extract),
   nop 0. If the oracle misses the thresholds in Docker, compare its
   /logs/verifier/ctrf.json numbers with CALIBRATION.md before touching thresholds.
4. Rubric: `harbor check tasks/aircraft-orbit-mapping -r ../tb3/docs/prompts/task-implementation.toml -m anthropic/claude-opus-5`
5. Human-written files (CI requires): tasks/aircraft-orbit-mapping/instruction.md (from
   docs/instruction_facts.md; must end with the exact "You have 14400 seconds…" sentence) and the
   four README.md sections. Then re-run static checks (instruction-suffix, absolute-path,
   test-file-references now become meaningful).
6. Internal red team: run claude-code once with the instruction + ../tb3/docs/prompts/hack-trial-prompt.md
   appended (strip "Do not cheat…" first, as CI does); harden anything that scores > 0.
7. Official trials (CI defaults, .github/harbor-run-defaults.yml):
   ```
   export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000
   harbor run -p tasks/aircraft-orbit-mapping --agent claude-code -m anthropic/claude-opus-5 --env docker --yes \
     --ae CLAUDE_FORCE_OAUTH=1 --ae CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN --ak reasoning_effort=max -o jobs --job-name run-claude-1
   harbor run -p tasks/aircraft-orbit-mapping --agent codex -m openai/gpt-5.6-sol --env docker --yes \
     --ae CODEX_FORCE_AUTH_JSON=1 --ak reasoning_effort=xhigh -o jobs --job-name run-codex-1
   ```
   ×3 each; then 1 cheat trial each on a copy of the task with the adversarial instruction.
   `harbor analyze <job-dir> -m sonnet -r ../tb3/docs/prompts/trial-analysis.toml --job-prompt ../tb3/docs/prompts/trial-analysis-job.txt`
   Infra failures (rate limit, crash, timeout) are re-run, never counted.
8. Docs: RESULTS.md (commands, configs, reward table, timings), FAILURE_ANALYSIS.md,
   CHEAT_ANALYSIS.md, CHECKS.md; commit jobs' ctrf/analyze JSON (not the full job dirs).

## Known open items
- solve.sh was written without a Docker run: apt names (ros-humble-libg2o, libpcl-dev…), Fast DDS
  SHM profile, `ros2 bag play -s mcap` flags are UNVERIFIED — step 3 will surface them.
- extract_aircraft.py leaves ~1.6 % apron points (gate 2 %) — fine, but tight; raise
  `--ground-clearance` to 0.25 if Docker runs land above 2 %.
- HF write token was pasted in chat on 2026-09-16 — revoke it after the upload.
