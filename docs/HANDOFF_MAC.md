# Handoff — continuing on the Mac

> **Superseded work log, kept for provenance.** Written while the work was in progress; its plans, counts and
> "remaining work" lists were overtaken by events. `RESULTS.md`, `CHECKS.md` and `docs/CALIBRATION.md` are the
> current record.

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

## Progress on the Mac (2026-09-16, evening)
Done: one-time setup (uv, harbor 0.23.0, codex 0.154.0 already logged in, tb3 clone), 22/22 static checks,
verifier unit tests 27/27, both images built (amd64), nop → reward 0, oracle by hand → reward 1 after three fixes
(see docs/CALIBRATION.md "Docker run 1"): `fastdds_profile.xml` element name, bounded shutdown in `solve.sh`,
`extract_aircraft.py` default clearance 0.40. The "Known open items" above are resolved by these.

Constraints found: this Mac has 8 GB RAM. Docker at 7 GB with `BUILD_JOBS=1` is the minimum that builds; the
task's declared 4 CPU / 16 GB is not reproducible locally, and amd64 emulation drops ~19 % of scans at 0.5x and
yields no loop closures. Use `--env modal` (the TB3 CI default) for the harbor oracle/nop validation and for all
trials; keep the local Docker path for shaking out scripts only. `modal` CLI is installed; `modal setup` and
`gh auth login` / `claude setup-token` are still to be done by hand.

Consider for CI robustness: `colcon build --parallel-workers 2` with `-j2` runs four cc1plus at once; on the
4 CPU / 16 GB CI box that is ~12 GB peak. `BUILD_JOBS=1` costs ~2 min and halves it.

## State at 2026-09-16 19:45 EDT
Gates: static 22/22; rubric 32/0/3 (three attempts, see CHECKS.md); Modal oracle 3/3 reward 1; Modal nop 0; instruction.md
and README sections written. Repo made private before cheat trials. Trials: run-codex-1 reward 0 (genuine crux failure,
analyzed); cheat-codex-1 reward 0 but OpenAI refused the red-team brief (two attempts); run-claude-1, run-claude-2,
run-codex-2 in flight on Modal. Remaining: run-claude-3, run-codex-3, cheat-claude-1, `harbor analyze` on every job,
final RESULTS / FAILURE_ANALYSIS / CHEAT_ANALYSIS tables, commit.

Launch scripts (session scratchpad, read the token files there): `run_claude_trial.sh <N|cheat>`,
`run_codex_trial.sh <N|cheat>`, `run_rubric.sh`, `run_analyze.sh <job-dir>`. Auth lessons: harbor's claude-code under
subscription OAuth needs exact model ids (`claude-opus-5`, `claude-sonnet-5`, no `anthropic/` prefix, no aliases);
`harbor exec` mangles `--ae`, so export `CLAUDE_FORCE_OAUTH=1` + token in the host env; codex must use `OPENAI_API_KEY`
(a ChatGPT-account login cannot use gpt-5.6-sol; `CODEX_FORCE_AUTH_JSON=1` always reads `~/.codex/auth.json`).

## Complete — 2026-09-17 02:30 UTC
All gates and all eight trials are done; see `CHECKS.md`, `RESULTS.md`, `FAILURE_ANALYSIS.md`, `CHEAT_ANALYSIS.md`.
Backends: Modal until its free-tier spend cap was reached, then harbor's `docker` backend on a GCP `e2-standard-4`
(4 vCPU / 16 GB, the task's declared resources). The VM `tb3-runner` (us-central1-a, project terminalbench-508900) is
left running at the author's request; `gcloud compute instances stop tb3-runner --zone us-central1-a` halts compute
billing, `... delete ...` removes it.

Remaining optional work: `harbor analyze` on run-claude-3 and both cheat jobs (the other five trials are analyzed);
the metric revision proposed at the end of `FAILURE_ANALYSIS.md` (exclude sub-reference-surface halo points from the
precision denominator, then recalibrate every baseline from scratch) if the task is ever submitted to TB3 proper.
