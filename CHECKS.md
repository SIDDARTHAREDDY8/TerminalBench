# CHECKS — automated checks required by the TB3 CI

Everything below was run against `tasks/aircraft-orbit-mapping` with the TB3 checkout at commit `e2995b9`
(2026-09-11, `harbor-framework/terminal-bench`, then still named `terminal-bench-3`) and harbor 0.23.0.

## 1. Static checks (22) — PASS

```
for c in ../tb3/scripts/checks/check-*.sh; do bash "$c" tasks/aircraft-orbit-mapping; done
```
Output: `docs/runs/2026-09-16-static-checks/results.txt` (22 PASS, 0 FAIL, no warnings). Run after `instruction.md`
and the README sections were written, so `check-instruction-suffix`, `check-task-absolute-path` and
`check-test-file-references` are meaningful.

## 2. Verifier unit tests — PASS

```
uv run --python 3.11 --with numpy==1.26.4 --with scipy==1.13.1 --with plyfile==1.1 --with pytest==9.1.1 \
  python -m pytest tools/calibration/test_verify_lib.py -q
```
27 passed in 106 s.

## 3. Docker build — PASS

```
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t aom-env   tasks/aircraft-orbit-mapping/environment   # 3.87 GB, bag SHA-256 verified
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t aom-tests tasks/aircraft-orbit-mapping/tests         # 126 MB
```
Both built on an Apple Silicon Mac under Rosetta (the CI builds on x86-64; `ros:humble-ros-base` is multi-arch and
no `--platform` is pinned in either Dockerfile).

## 4. Nop validation — reward 0 (local Docker and harbor on Modal)

Exact CI form (`validate_env: modal`):
```
harbor run -p tasks/aircraft-orbit-mapping --agent nop --env modal -o jobs --job-name validate-nop-1
```
2026-09-16: 1/1 trials, 0 exceptions, Mean 0.000 — `docs/runs/validate-nop-1/` (result.json, verifier ctrf.json, reward.txt).

Local, by hand:

```
docker run --rm aom-tests bash /tests/test.sh
```
5 errors ("missing deliverable"), CTRF written, `reward.txt` = 0.

## 5. Oracle validation — reward 1 (3/3 on the CI backend + 2 local Docker runs)

Local, by hand (the Mac has 8 GB RAM; the task declares 16 GB):
```
docker run --name aom-oracle --cpus 6 --memory 7g -e BUILD_JOBS=1 -v $PWD/tasks/aircraft-orbit-mapping/solution:/solution:ro aom-env bash /solution/solve.sh
docker cp aom-oracle:/app/trajectory.tum out/; docker cp aom-oracle:/app/aircraft.ply out/
docker run --rm -v $PWD/out:/app:ro -v $PWD/logs:/logs/verifier aom-tests bash /tests/test.sh
```
5/5 passed, reward 1 — `docs/runs/2026-09-16-mac-docker/ctrf.json`; numbers in `docs/CALIBRATION.md` ("Docker run 1").
Three oracle bugs were found and fixed on the way (Fast DDS profile element name, bounded shutdown of `ros2 launch`,
ground clearance 0.20 → 0.40 m); the first oracle attempt was OOM-killed at a 6 GB container cap.

Exact CI form on Modal (the TB3 `validate_env` default) — **reward 1.0**, 0 exceptions (`validate-oracle-1`, 2026-09-16):
environment build 4 min 11 s (bag SHA-256 verified inside Modal), oracle 10 min 33 s at the declared 4 CPU / 16 GB,
verifier 2 min 10 s; metrics re-accumulation 0.813 / 0.995, model 0.804 / 0.989, junk 0.146, apron 0.0 %
(`docs/runs/validate-oracle-1/`). Repeats `validate-oracle-2` and `-3` (image cached): reward 1.0 each, oracle 9 min 54 s, metrics identical to three decimals
(`docs/runs/validate-oracle-2/`, `-3/`). Oracle on the CI backend: **3/3**.
```
harbor run -p tasks/aircraft-orbit-mapping --agent oracle --env modal -o jobs --job-name validate-oracle-N   # N = 1, 2, 3
```

## 6. Implementation rubric review — PASS (32 pass / 0 fail / 3 n/a of 35)

CI runs the reviewer as a harbor job (`review.yml`): the task is staged at `/app/task-under-review/<name>/` with the
rubric at `/app/rubric.toml`, and `claude-code -m sonnet` writes `/app/verdicts.json`. Reproduced locally with:
```
STAGE=$(mktemp -d); mkdir "$STAGE/task-under-review"; cp -R tasks/aircraft-orbit-mapping "$STAGE/task-under-review/"
cp ../tb3/docs/prompts/task-implementation.toml "$STAGE/rubric.toml"
harbor exec -p "$STAGE/task-under-review" -p "$STAGE/rubric.toml" \
  --instruction-path ../tb3/scripts/rubric-regression/templates/instruction.md \
  -f /app/verdicts.json --image ubuntu:24.04 -a claude-code -m sonnet --job-name rubric-review \
  --ae CLAUDE_FORCE_OAUTH=1 --ae CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN
```
Two deviations from the CI command, both forced by subscription OAuth instead of an API key: `harbor exec` mangles `--ae`
values, so `CLAUDE_FORCE_OAUTH=1` and the token are exported in the host environment instead; and the OAuth path
rejects the `sonnet` alias, so the exact id `claude-sonnet-5` (what the alias resolves to) is passed. The reviewer
model, rubric, instruction template and staging layout are otherwise identical to `review.yml`.
Three attempts, verdicts in `docs/runs/rubric-review/` (`verdicts.json`, `verdicts_rerun.json`, `verdicts_attempt3.json`):

| attempt | pass / fail / n/a | failed criteria and what changed |
|---|---|---|
| 1 | 25 / 8 / 2 | `verifiable`, `deterministic_reproducible`, `verification_explanation_quality`, `reviewable` (thresholds.json still said `"calibrated": false` and cited scratch paths); `solvable` (solve.sh header still said UNVERIFIED); `*_explanation_quality` ×3 (fields absent from task.toml); `no_extraneous_files` (`__pycache__` from local test runs). Fixed: provenance rewritten with the measured numbers (no threshold changed), solve.sh header rewritten, explanations added to task.toml, calibration record added to the task README, caches removed. |
| 2 | 32 / 1 / 2 | `task_readme` — README sections were now verbatim copies of the task.toml fields. Fixed: task.toml fields condensed to one-to-two-sentence versions that point to the README. |
| 3 | 32 / 0 / 3 | n/a: `artifact_efficiency`, `verifier_execution_isolation`, `do_not_modify_enforced` — all correctly not applicable. |

Static checks re-run after every change: 22/22. A manual pass over all 35 criteria is in `docs/RUBRIC_SELF_REVIEW.md`.
