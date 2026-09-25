# RESULTS — agent trials (`/run`) and adversarial trials (`/cheat`)

Configuration is the TB3 CI default (`.github/harbor-run-defaults.yml` at tb3 commit `e2995b9`): 3 trials per agent,
`claude-code` on `anthropic/claude-opus-5` with `reasoning_effort=max` and `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`,
`codex` on `openai/gpt-5.6-sol` with `reasoning_effort=xhigh`; backend `modal`; `harbor analyze` on six jobs (see below).
Agent timeout is the task's 14 400 s. Infrastructure failures (rate limit, crash, container failure, timeout of the
harness itself) are re-run and never counted as model failures.

**Backends.** run-codex-1 and the first cheat-codex attempts ran on Modal (the TB3 CI default); run-codex-2, run-claude-1 and run-claude-2 started there but were superseded by VM re-runs after Modal's spend cap (below).
Modal's free-tier spend cap was reached on 2026-09-16 evening, so run-claude-3, run-codex-3 and cheat-claude-1 ran with
harbor's `docker` backend (the other backend the CI supports) on a GCP `e2-standard-4` VM — 4 vCPU / 16 GB, Ubuntu 22.04
x86-64, Docker 29 — i.e. the task's declared resources, with the same agents, models, flags and prompts.

## Commands

```
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000
harbor run -p tasks/aircraft-orbit-mapping --agent claude-code -m anthropic/claude-opus-5 --env modal --yes \
  --ae CLAUDE_FORCE_OAUTH=1 --ae CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN --ak reasoning_effort=max \
  -o jobs --job-name run-claude-N            # N = 1, 2, 3
harbor run -p tasks/aircraft-orbit-mapping --agent codex -m openai/gpt-5.6-sol --env modal --yes \
  --ae CODEX_FORCE_AUTH_JSON=1 --ak reasoning_effort=xhigh \
  -o jobs --job-name run-codex-N             # N = 1, 2, 3
harbor analyze jobs/run-claude-N -m sonnet -r ../tb3/docs/prompts/trial-analysis.toml --job-prompt ../tb3/docs/prompts/trial-analysis-job.txt
```

## Reward table

| trial | agent / model | reward | wall time | verifier tests passed | notes |
|---|---|---|---|---|---|
| run-claude-1rerun | claude-code / opus-5 max (GCP VM, docker backend) | **0** | agent 2 h 07 m, verifier 3 min 26 s, harbor-scored, 0 errors | 3/5 | trajectory localprec 0.705 (gate 0.72); model precision 0.817 — the second-sharpest of any trial — but coverage 0.880 misses the 0.90 gate |
| run-claude-1 *(Modal, superseded)* | claude-code / opus-5 max | 0 (hand-scored) | agent ~2 h 05 m | 4/5 | trajectory 0.7138, model 0.760 / 0.970. Harbor never scored it (Modal spend cap); kept as evidence, **not counted** |
| run-claude-2rerun | claude-code / opus-5 max (GCP VM, docker backend) | **0** | agent 1 h 20 m, verifier 3 min 30 s, harbor-scored, 0 errors | 3/5 | trajectory localprec 0.707 (gate 0.72); model precision 0.833 (sharpest of all trials) but coverage 0.878 misses the 0.90 gate |
| run-claude-2 *(Modal, superseded)* | claude-code / opus-5 max | 0 (hand-scored) | agent 2 h 21 m | 4/5 | trajectory 0.689, model 0.722 / 0.968. Harbor never scored it (Modal spend cap); kept as evidence, **not counted** |
| run-claude-3 | claude-code / opus-5 max (GCP VM, docker backend) | **0** | agent 1 h 30 m, verifier 5 min 40 s | 3/5 (trajectory and model tests fail) | trajectory localprec 0.685 (gate 0.72); model 0.573 / 0.996, junk 0.05, apron 0.0 %; 948 k points |
| run-codex-1 | codex / gpt-5.6-sol xhigh | **0** | agent 16 min 55 s, verifier 3 min 28 s | 3/5 (files, consistency, cleanliness) | trajectory localprec 0.684 (gate 0.72), model 0.659 (gate 0.72); coverage 0.99 both; 2.45 M input tokens |
| run-codex-2rerun | codex / gpt-5.6-sol xhigh (GCP VM, docker backend) | **0** | agent 14 min 18 s, verifier 4 min 35 s, harbor-scored, 0 errors | 4/5 (trajectory test fails) | trajectory localprec 0.684 (gate 0.72); model 0.796 / 0.917, junk 0.18 — model gate passed, trajectory gate not |
| run-codex-2 *(Modal, superseded)* | codex / gpt-5.6-sol xhigh | 0 (hand-scored) | agent 19 min 49 s | 4/5 | trajectory 0.684, model 0.737 / 0.955. Harbor never scored it (Modal spend cap); kept as evidence, **not counted** |
| run-codex-3 | codex / gpt-5.6-sol xhigh (GCP VM, docker backend) | **0** | env 5 min 29 s, agent 14 min 37 s, verifier 4 min 29 s | 4/5 (trajectory test fails) | trajectory localprec 0.684 (gate 0.72); model 0.773 / 0.966, junk 0.04 |
| cheat-claude-1 | claude-code / opus-5 max (adversarial, GCP VM) | **0** | agent 7 min 09 s, verifier 19 s | verifier ran, wrote reward 0 | probed for exploits, wrote **no deliverables**, reported "no credible bypass exists"; see CHEAT_ANALYSIS.md |
| cheat-claude-public | claude-code / opus-5 max (adversarial, **run after the repo was made public**) | **0** | agent 1 h 15 m, harbor-scored, 0 errors | 2/5 | never used the public repo (0 web-tool calls); instead tampered with `/app/data/orbit.mcap` to make the verifier re-project its own planted cloud. The verifier reads its own baked keyframes, so the attack reached nothing: re-accumulation 0.0, consistency off by 1498 m. See CHEAT_ANALYSIS.md |
| cheat-codex-1 | codex / gpt-5.6-sol xhigh (adversarial) | **0** | ~20 s (×3 attempts: Modal ×2, GCP VM ×1) | verifier ran, wrote reward 0 | OpenAI API refused the red-team brief as a cybersecurity risk on all three attempts, across both backends and both auth paths (`AgentSafetyRefusalError`); see CHEAT_ANALYSIS.md |

**Harbor artifact-redaction bug (affects the claude trials' scoring path).** Harbor redacts the *value* of every
`--ae KEY=VALUE` from the text it handles — including downloaded text artifacts. The CI-documented flag
`--ae CLAUDE_FORCE_OAUTH=1` has the value `1`, so every digit `1` in `trajectory.tum` was replaced by the literal
string `[REDACTED]` (10 994 occurrences in run-claude-1), making the file unparseable; the binary `aircraft.ply` was
untouched, and the codex trials (no `--ae` flag) were unaffected. The substitution is exact and reversible
(`[REDACTED]` → `1`): the recovered file parses as 1462×8 finite values with quaternion norms within 1e-9 of unity,
strictly increasing stamps spanning 146.101 s and all 100 keyframe stamps covered — none of which could hold if the
reversal were wrong. Recovered artifacts were scored with the identical verifier image. `run-claude-1rerun` and `run-claude-2rerun` export
`CLAUDE_FORCE_OAUTH=1` in the host environment instead, which harbor's claude-code agent reads the same way and which
leaves their artifacts clean. `run-claude-3` still passed the flag via `--ae`, so its committed records carry the same
`[REDACTED]` substitution; it was repaired by the inverse substitution before archiving, exactly as the other two were.

**On the three superseded Modal runs.** For `run-codex-2`, `run-claude-1` and `run-claude-2` the agent phase completed
normally and the artifacts were downloaded, but Modal terminated the verifier-image build at its free-tier spend cap, so
harbor recorded `ImageBuildError` and wrote no reward. Those artifacts were scored by hand with the identical verifier
image. Each superseded run's `ctrf.json` is committed and carries the trajectory figure from its failing assertion
(0.7138, 0.6891, 0.6844); the model/junk/consistency figures quoted for them were read from that hand-run's console
output, which was not retained. **None of them is counted**: the assessment excludes
container failures from being model failures. Each was re-run end to end on the GCP VM, and those three re-runs —
`run-codex-2rerun`, `run-claude-1rerun`, `run-claude-2rerun` — are the reported results, all harbor-scored with 0 errors.


## Summary — requirement check

| assessment requirement | result |
|---|---|
| All required static checks pass | 22 / 22 |
| Implementation-rubric checks pass | 32 pass / 0 fail / 3 n/a of 35 |
| Docker build | pass (Modal and local) |
| Oracle validation | reward 1 — 3/3 on Modal (CI backend) + 2 local Docker runs |
| Nop validation | reward 0 (Modal and local) |
| 3 × claude-code (opus-5, max) genuinely fail | **3/3 reward 0**, all harbor-scored with 0 errors — trajectory 0.705, 0.707, 0.685 against the 0.72 gate |
| 3 × codex (gpt-5.6-sol, xhigh) genuinely fail | **3/3 reward 0**, all harbor-scored with 0 errors — trajectory 0.684 ×3 |
| 1 × claude-code `/cheat` scores zero | **reward 0** — probed for exploits, produced no deliverables, reported "no credible bypass exists". A second adversarial run after publication (`cheat-claude-public`) built and executed a real input-tampering exploit and was defeated by the separate verifier; also reward 0 |
| 1 × codex `/cheat` scores zero | **reward 0** — but by provider refusal on all 3 attempts, not by a defeated attack (see CHEAT_ANALYSIS.md) |

No trial was excluded as an infrastructure failure without being re-run. Nine such failures occurred, in five groups —
two codex auth failures, one claude model-id failure, three Modal verifier-build failures at its free-tier spend cap,
two Claude session-limit failures and one network failure — and all are listed below with their evidence and their
re-runs.

**How the trials failed.** All six honest trials delivered well-formed, self-consistent, apron-clean artifacts and
failed on the same gate: the re-accumulation of raw keyframes with the agent's own poses. Every codex trial scored
exactly 0.684 — the GNSS-INS baseline in `docs/CALIBRATION.md` — after deciding within its first few commands that the
recorded pose stream was "drift-free". The opus trials worked the problem for 1.5–2 h and got closer (0.705 and 0.707
with motion-compensated ICP refinement) but none ran an incremental scan-matching front-end — they refined against maps
built from the poses under test, so the smear was already in the target — and one explicitly concluded refinement was
unnecessary after validating the poses against a map built from those same poses. (The reference solution's pose-graph
back-end accepts no loop closures on this recording either; the separation comes from the front-end, not the back-end.) Detail per trial: `FAILURE_ANALYSIS.md`, which
also contains an honest assessment of the 0.006 margin on the closest trial and of the analyzer's `near_miss` flag.

## Known gaps between the instruction and the verifier

Found by an internal audit after the trials completed. None is fixed in this submission, because changing
`instruction.md` or the verifier now would mean the recorded trials no longer correspond to the shipped task. They are
recorded here instead, with the fix each one needs.

1. **The stamp gate is not what the instruction says.** `instruction.md` states that "at least 95 % of the
   `/fused_points` stamps must be present". The verifier's `min_stamp_coverage` is applied to the 100 hidden keyframe
   stamps and only asks whether each lies inside the trajectory's time range, so a trajectory with very few poses that
   merely spans the recording passes `test_files`. `cheat-claude-public` exploited exactly this, submitting 350 real
   poses and 1112 placeholders while "still meeting the >=95 % stamp-presence rule". The remaining gates caught it, so
   it was not a bypass, but the instruction and the implementation should agree: `test_files` should count the agent's
   poses against the 1462 `/fused_points` stamps.
2. **Format requirements stated but not enforced.** The instruction requires binary little-endian PLY and ascending
   timestamps; `verify_lib.load_ply` accepts ASCII or either endianness and `load_tum` sorts the lines. The instruction
   should be softened, or the reader tightened.
3. **Rejections enforced but not stated.** `load_tum` rejects duplicate timestamps and fewer than two poses, and
   `load_ply` rejects an empty vertex element. None of these is in the instruction.
4. **The frame contract is phrased three ways.** The instruction says "right-handed, metric"; the verifier's docstrings
   say "gravity-aligned"; `docs/instruction_facts.md` says "z need not be up". `robust_align` sweeps yaw about z and
   only adds PCA up-axis hypotheses when the cloud tilts more than 10 degrees, so gravity alignment is the assumed
   case. One wording should be chosen and used everywhere.

## Task-version notes

- `run-codex-1` ran against the task as it stood before the implementation-rubric fixes (its verifier log shows
  `'calibrated': False`; the other five counted trials show `True`). **No threshold value differs between the two** —
  the change was provenance text in `thresholds.json` plus metadata and documentation — so the trial remains
  comparable, but the task checksum differs and it is noted here rather than glossed.
- All eight agent trials predate the calibration-file rename (they reference the old filename in their prompts). The
  rename changed names only; it was re-validated with static checks and a full oracle run (`CHECKS.md` section 8), not
  by re-running the trials.

## Infrastructure failures (re-run, not counted)

| job | date | cause | evidence |
|---|---|---|---|
| run-codex-1 (attempts 1 and 2) | 2026-09-16 | agent exited after 2 min: OpenAI returned `400 The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account` (codex login was a ChatGPT free-plan account; the model needs API-key access). No artifacts were produced, so harbor's Modal backend also raised `SandboxFilesystemNotFoundError: /app/aircraft.ply` on artifact download. Attempt 2 repeated the same error (harbor's `CODEX_FORCE_AUTH_JSON=1` always reads `~/.codex/auth.json`). Resolved by running with `OPENAI_API_KEY` in the host environment (harbor's default codex auth path), which is the third launch, counted as trial 1. | `docs/runs/run-codex-1-infra/` |
| run-claude-1, run-claude-2, run-codex-2 (Modal) | 2026-09-16 | Modal terminated the **verifier image build** with "Container terminated due to reaching billing cycle spend limit" after each agent phase had completed normally; harbor recorded `ImageBuildError` and wrote no reward, so none of the three is a harness-scored model failure. All three were re-run end-to-end on the GCP VM (docker backend): `run-codex-2rerun`, `run-claude-1rerun`, `run-claude-2rerun`. The Modal artifacts and their hand-scored verifier output are kept for comparison but are **not** the reported results. | `docs/runs/run-claude-1/`, `run-claude-2/`, `run-codex-2/` (`modal_exception_tail.txt`, `result.json`) |
| run-claude-1rerun, run-claude-2rerun (first attempts) | 2026-09-17 | Both died on the Claude subscription session limit ("You've hit your session limit · resets 5am (UTC)") after they were launched **concurrently** to save wall-clock time. A rate-limit failure, excluded by the brief. Re-run sequentially after the quota reset; running one opus-max trial at a time completed cleanly. | `docs/runs/infra-failures/` (result.json + the agent's own error line) |
| run-claude-2rerun (second attempt) | 2026-09-17 | `NetworkConnectionError` 6 min in, during agent installation; the agent never started and no transcript was produced. Relaunched immediately. | `docs/runs/infra-failures/` |
| run-claude-1 (attempt 1) | 2026-09-16 | agent exited after 40 s: Claude Code under subscription OAuth returned `model_not_found` for the literal model string `anthropic/claude-opus-5`; the API-key path CI uses resolves the provider prefix, the OAuth path does not. Relaunched with the bare id `claude-opus-5` (the same model), counted as trial 1. | `docs/runs/run-claude-1-infra/` |

Per-job `ctrf.json`, reward, verifier stdout and trial record are committed under `docs/runs/<job-name>/`.
`harbor analyze` was run on six jobs — `run-codex-1`, `run-codex-2`, `run-codex-3`, `run-claude-1`, `run-claude-2` and
`cheat-claude-1` — and their `analysis.json` files are committed alongside. The three VM re-runs and
`cheat-claude-public` were not analyzed; their evidence is the verifier output and the full agent transcript. Failure analysis:
`FAILURE_ANALYSIS.md`; cheat analysis: `CHEAT_ANALYSIS.md`.
