# RESULTS — agent trials (`/run`) and adversarial trials (`/cheat`)

Configuration is the TB3 CI default (`.github/harbor-run-defaults.yml` at tb3 commit `e2995b9`): 3 trials per agent,
`claude-code` on `anthropic/claude-opus-5` with `reasoning_effort=max` and `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`,
`codex` on `openai/gpt-5.6-sol` with `reasoning_effort=xhigh`; backend `modal`; `harbor analyze -m sonnet` on every job.
Agent timeout is the task's 14 400 s. Infrastructure failures (rate limit, crash, container failure, timeout of the
harness itself) are re-run and never counted as model failures.

**Backends.** run-codex-1, run-codex-2, run-claude-1, run-claude-2 and cheat-codex-1 ran on Modal (the TB3 CI default).
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
| run-claude-1rerun | claude-code / opus-5 max (GCP VM, docker backend) | **0** | agent ~2 h 12 m, harbor-scored, 0 errors | 3/5 | trajectory localprec 0.705 (gate 0.72); model precision 0.817 — the sharpest model of any trial — but coverage 0.880 misses the 0.90 gate |
| run-claude-1 *(Modal, superseded)* | claude-code / opus-5 max | 0 (hand-scored) | agent ~2 h 05 m | 4/5 | trajectory 0.7138, model 0.760 / 0.970. Harbor never scored it (Modal spend cap); kept as evidence, **not counted** |
| run-claude-2 | claude-code / opus-5 max | **0** | agent ~2 h; verifier re-run locally | 4/5 (trajectory test fails) | trajectory localprec 0.689 (gate 0.72); model 0.722 / 0.968, junk 0.06, apron 0.0 %; 1.25 M points |
| run-claude-3 | claude-code / opus-5 max (GCP VM, docker backend) | **0** | agent ~1 h 40 m, verifier 4 min | 3/5 (trajectory and model tests fail) | trajectory localprec 0.685 (gate 0.72); model 0.573 / 0.996, junk 0.05, apron 0.0 %; 948 k points |
| run-codex-1 | codex / gpt-5.6-sol xhigh | **0** | agent 16 min 55 s, verifier 3 min 28 s | 3/5 (files, consistency, cleanliness) | trajectory localprec 0.684 (gate 0.72), model 0.659 (gate 0.72); coverage 0.99 both; 2.45 M input tokens |
| run-codex-2 | codex / gpt-5.6-sol xhigh | **0** | agent 19 min 49 s; verifier re-run locally (see note) | 4/5 (trajectory test fails) | trajectory localprec 0.684 (gate 0.72); model 0.737 / 0.955, junk 0.06 — model gate passed, trajectory gate not |
| run-codex-3 | codex / gpt-5.6-sol xhigh (GCP VM, docker backend) | **0** | env 5 min 29 s, agent 14 min 37 s, verifier 4 min 29 s | 4/5 (trajectory test fails) | trajectory localprec 0.684 (gate 0.72); model 0.773 / 0.966, junk 0.04 |
| cheat-claude-1 | claude-code / opus-5 max (adversarial, GCP VM) | **0** | agent 7 min 09 s | verifier ran, wrote reward 0 | probed for exploits, wrote **no deliverables**, reported "no credible bypass exists"; see CHEAT_ANALYSIS.md |
| cheat-codex-1 | codex / gpt-5.6-sol xhigh (adversarial) | **0** | ~20 s (×3 attempts: Modal ×2, GCP VM ×1) | verifier ran, wrote reward 0 | OpenAI API refused the red-team brief as a cybersecurity risk on all three attempts, across both backends and both auth paths (`AgentSafetyRefusalError`); see CHEAT_ANALYSIS.md |

**Harbor artifact-redaction bug (affects the claude trials' scoring path).** Harbor redacts the *value* of every
`--ae KEY=VALUE` from the text it handles — including downloaded text artifacts. The CI-documented flag
`--ae CLAUDE_FORCE_OAUTH=1` has the value `1`, so every digit `1` in `trajectory.tum` was replaced by the literal
string `[REDACTED]` (10 994 occurrences in run-claude-1), making the file unparseable; the binary `aircraft.ply` was
untouched, and the codex trials (no `--ae` flag) were unaffected. The substitution is exact and reversible
(`[REDACTED]` → `1`): the recovered file parses as 1462×8 finite values with quaternion norms within 1e-9 of unity,
strictly increasing stamps spanning 146.101 s and all 100 keyframe stamps covered — none of which could hold if the
reversal were wrong. Recovered artifacts were scored with the identical verifier image. Subsequent runs export
`CLAUDE_FORCE_OAUTH=1` in the host environment instead, which harbor's claude-code agent reads the same way and which
leaves artifacts clean.

**Note on run-codex-2 scoring.** The agent phase completed normally on Modal and both artifacts were downloaded, but
Modal terminated the verifier-image build with "Container terminated due to reaching billing cycle spend limit" (the
workspace's monthly cap; the image had to be rebuilt because `tests/thresholds.json`'s comment had changed). The
downloaded artifacts were scored on the same Mac with the identical verifier image (`aom-tests`, built from the same
`tests/` directory) — the verifier is deterministic and data-only, so the result is the one Modal would have produced.
CTRF: `docs/runs/run-codex-2/ctrf.json`; Modal's exception: `docs/runs/run-codex-2/modal_exception_tail.txt`.


## Summary — requirement check

| assessment requirement | result |
|---|---|
| All required static checks pass | 22 / 22 |
| Implementation-rubric checks pass | 32 pass / 0 fail / 3 n/a of 35 |
| Docker build | pass (Modal and local) |
| Oracle validation | reward 1 — 3/3 on Modal (CI backend) + 2 local Docker runs |
| Nop validation | reward 0 (Modal and local) |
| 3 × claude-code (opus-5, max) genuinely fail | **3/3 reward 0** — 0.714, 0.689, 0.685 against the 0.72 trajectory gate |
| 3 × codex (gpt-5.6-sol, xhigh) genuinely fail | **3/3 reward 0** — 0.684 ×3 |
| 1 × claude-code `/cheat` scores zero | **reward 0** — probed for exploits, produced no deliverables, reported "no credible bypass exists" |
| 1 × codex `/cheat` scores zero | **reward 0** — but by provider refusal on all 3 attempts, not by a defeated attack (see CHEAT_ANALYSIS.md) |

No trial was excluded as an infrastructure failure without being re-run; the four infrastructure failures that did occur
(two codex auth, one claude model-id, and three Modal verifier-build failures when its free-tier spend cap was reached) are listed below with their evidence and their re-runs.

**How the trials failed.** All six honest trials delivered well-formed, self-consistent, apron-clean artifacts and
failed on the same gate: the re-accumulation of raw keyframes with the agent's own poses. Every codex trial scored
exactly 0.684 — the GNSS-INS baseline in `docs/CALIBRATION.md` — after deciding within its first few commands that the
recorded pose stream was "drift-free". The opus trials worked the problem for 1.5–2 h and got closer (0.714 with
motion-compensated ICP refinement) but none used loop closure, and one explicitly concluded refinement was unnecessary
after validating the poses against a map built from those same poses. Detail per trial: `FAILURE_ANALYSIS.md`, which
also contains an honest assessment of the 0.006 margin on the closest trial and of the analyzer's `near_miss` flag.

## Infrastructure failures (re-run, not counted)

| job | date | cause | evidence |
|---|---|---|---|
| run-codex-1 (attempts 1 and 2) | 2026-09-16 | agent exited after 2 min: OpenAI returned `400 The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account` (codex login was a ChatGPT free-plan account; the model needs API-key access). No artifacts were produced, so harbor's Modal backend also raised `SandboxFilesystemNotFoundError: /app/aircraft.ply` on artifact download. Attempt 2 repeated the same error (harbor's `CODEX_FORCE_AUTH_JSON=1` always reads `~/.codex/auth.json`). Resolved by running with `OPENAI_API_KEY` in the host environment (harbor's default codex auth path), which is the third launch, counted as trial 1. | `docs/runs/run-codex-1-infra/` |
| run-claude-1, run-claude-2, run-codex-2 (Modal) | 2026-09-16 | Modal terminated the **verifier image build** with "Container terminated due to reaching billing cycle spend limit" after each agent phase had completed normally; harbor recorded `ImageBuildError` and wrote no reward, so none of the three is a harness-scored model failure. All three were re-run end-to-end on the GCP VM (docker backend): `run-codex-2rerun`, `run-claude-1rerun`, `run-claude-2rerun`. The Modal artifacts and their hand-scored verifier output are kept for comparison but are **not** the reported results. | `docs/runs/run-claude-1/`, `run-claude-2/`, `run-codex-2/` (`modal_exception_tail.txt`, `result.json`) |
| run-claude-1 (attempt 1) | 2026-09-16 | agent exited after 40 s: Claude Code under subscription OAuth returned `model_not_found` for the literal model string `anthropic/claude-opus-5`; the API-key path CI uses resolves the provider prefix, the OAuth path does not. Relaunched with the bare id `claude-opus-5` (the same model), counted as trial 1. | `docs/runs/run-claude-1-infra/` |

Per-job `ctrf.json` and `harbor analyze` output are committed under `docs/runs/<job-name>/`. Failure analysis:
`FAILURE_ANALYSIS.md`; cheat analysis: `CHEAT_ANALYSIS.md`.
