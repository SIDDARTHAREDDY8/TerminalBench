# aircraft-orbit-mapping — a Terminal-Bench 3 task

Take-home for the Klavis AI Founding Engineer role: one original
[Terminal-Bench 3](https://github.com/harbor-framework/terminal-bench-3) task, built to the
current TB3 CI (static checks, implementation rubric, Docker build, oracle/nop validation,
`/run` and `/cheat` trials).

**Status: complete.** All TB3 CI gates pass, all six required agent trials fail genuinely, and both adversarial
trials score zero. Commands, configurations and results are in `CHECKS.md` (checks), `RESULTS.md` (trials),
`FAILURE_ANALYSIS.md` (why the agents fail, including a frank look at the closest margin) and `CHEAT_ANALYSIS.md`
(attack surface and adversarial trials).

## The task

A ground robot drove one orbit around a parked business jet on an open apron, recording five
LiDARs (a Hesai Pandar40P, four Livox Mid-360 and their fused cloud), a GNSS-INS, IMU, wheel
odometry and TF. The agent receives the raw recording and the robot's sensor-mount calibration
and must deliver a metric, drift-free model of the aircraft:

- `/app/trajectory.tum` — pose of `base_link` at every `/fused_points` stamp (TUM format)
- `/app/aircraft.ply` — the aircraft, and only the aircraft, in that same frame

The verifier (separate container) transforms a hidden set of raw keyframes with the agent's
poses and scores them against a hand-cleaned reference model built by an independent SLAM
run: local precision at 10 cm (drift/smear), coverage at 20 cm (completeness), plus
frame-consistency, apron-contamination and clutter gates. Reward is binary.

Why it is hard for a good reason: the open apron has too few features for scan-to-scan
odometry, and GNSS-INS heading noise over a 17 m lever arm smears every naive accumulation —
all measured shortcuts reach ≤ 0.68 local precision against the 0.72 gate, while a correctly
configured loop-closed SLAM reaches 0.80. The agent cannot see the reference, so it cannot
tell "looks like a jet" from "passes".

## Layout

```
tasks/aircraft-orbit-mapping/   the TB3 task (task.toml, instruction.md, README.md, environment/, solution/, tests/)
CHECKS.md                       commands + results of every CI check (static, build, oracle, nop, rubric)
RESULTS.md                      agent / cheat trial commands, configs and reward table
CHEAT_ANALYSIS.md               attack-surface analysis and /cheat trial outcomes
docs/CALIBRATION.md             measured oracle / baseline numbers behind the thresholds, incl. the Docker run
docs/RUBRIC_SELF_REVIEW.md      manual pass over the 35 implementation-rubric criteria
docs/instruction_facts.md       fact sheet the instruction.md was built from
docs/data_provenance.md         how orbit.mcap and the reference data were produced
docs/HANDOFF_MAC.md             running work log for the Docker/trial phase (internal notes, kept for provenance)
docs/runs/                      CTRF reports and logs of the recorded runs
docs/superpowers/specs/         design spec
tools/                          data-prep tooling and the verifier unit tests
```

## Progress

| Gate | Status |
|---|---|
| 22 TB3 static checks | pass (with instruction.md and README sections in place) |
| Verifier unit tests | 27/27 |
| Task data published | done — HF dataset `pinkman9/aircraft-orbit-mapping`, hash pinned in the Dockerfile |
| Docker build (environment + verifier images) | pass — including a from-scratch rebuild in the final end-to-end test |
| Nop through the verifier | reward 0 (harbor on Modal + local Docker) |
| Oracle through the verifier | reward 1 — 3/3 on Modal, 2 local Docker runs, and the clean-slate end-to-end test on the GCP VM |
| GNSS-INS shortcut | reward 0 (calibration) |
| Implementation rubric (`harbor exec` reviewer, sonnet-5) | pass — 32 / 0 fail / 3 n/a (`CHECKS.md`) |
| `/run` trials — 3× claude-code opus-5 max | **3/3 reward 0** (trajectory 0.714 / 0.689 / 0.685 vs gate 0.72) |
| `/run` trials — 3× codex gpt-5.6-sol xhigh | **3/3 reward 0** (trajectory 0.684 ×3) |
| `/cheat` trial — claude-code opus-5 max | **reward 0** — no bypass found, no deliverables written |
| `/cheat` trial — codex gpt-5.6-sol xhigh | **reward 0** — provider refused the red-team brief (3 attempts) |

The recording (2.92 GB) is not committed; `environment/Dockerfile` downloads it at build time from
the public dataset https://huggingface.co/datasets/pinkman9/aircraft-orbit-mapping and verifies its
SHA-256 (`docs/data_provenance.md`).

## Repository visibility

This repository is **private** and must stay private until the assessment has been reviewed. `tests/reference/aircraft_ref.ply`
(the hidden ground-truth model) and `tests/thresholds.json` are committed here, so making it public would hand any agent with
internet access the answer. The public dataset card that hosts the recording previously linked back here; it was rewritten on
2026-09-17 to describe only the sensor data, with no repository link and no indication the recording belongs to a benchmark
task. See `CHEAT_ANALYSIS.md`.

## Known limitations

Recorded plainly rather than buried:

- **Both adversarial trials hit model safety classifiers on the TB3 red-team brief.** OpenAI's API refused codex
  outright on all three attempts, so that trial never exercised the verifier at all; claude-code ran but had one
  reconnaissance command flagged (`api_refusal_category='cyber'`), forcing a mid-session model fallback. Both scored
  zero and `harbor analyze` records `reward_hacking: pass` for the claude-code probe, but the anti-cheat claim rests on
  that one partially degraded run plus the structural analysis in `CHEAT_ANALYSIS.md`, not on two clean adversarial runs.
- **`harbor analyze` flags `near_miss` on three analyzed trials.** The closest trial missed the trajectory gate by 0.006.
  `FAILURE_ANALYSIS.md` quantifies this, explains why the gate still separates the two measured populations cleanly, and
  specifies the metric correction that should be made (and recalibrated from scratch) rather than moving the threshold.
- **The agent image pre-installs a generic point-cloud stack** (numpy, scipy, open3d, mcap). The rubric prefers leaving
  dependency discovery to the agent; this is a deliberate judgement call recorded in `docs/RUBRIC_SELF_REVIEW.md` row 18.

## Author

Siddartha Reddy Chinthala. The ground-truth reference model and the vendored solver patches came from the robot platform's
team and are reused with permission; everything else — task design, tooling, verifier, calibration — is the author's work.
See `docs/data_provenance.md`.

