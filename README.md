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
odometry, and GNSS-INS heading noise over a 17 m lever arm smears every naive accumulation.
The author-measured baselines reach ≤ 0.68 local precision against the 0.72 gate; the agent
trials did better with their own refinement, topping out at 0.707, and still fell short; the
reference solution reaches 0.80–0.81. What closes that gap is an incremental scan-matching
front-end — registering each scan against a map assembled from the scans already placed —
not the pose-graph back-end, which accepts no loop closures on this single-orbit recording
(see `docs/CALIBRATION.md` and `FAILURE_ANALYSIS.md`). The agent cannot see the reference, so
it cannot tell "looks like a jet" from "passes".

## Layout

```
tasks/aircraft-orbit-mapping/   the TB3 task (task.toml, instruction.md, README.md, environment/, solution/, tests/)
LICENSE                         MIT for this work; third-party components keep their own licenses
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
| `/run` trials — 3× claude-code opus-5 max | **3/3 reward 0** (trajectory 0.705 / 0.707 / 0.685 vs gate 0.72) |
| `/run` trials — 3× codex gpt-5.6-sol xhigh | **3/3 reward 0** (trajectory 0.684 ×3) |
| `/cheat` trial — claude-code opus-5 max | **reward 0** — no bypass found, no deliverables written |
| `/cheat` re-run after publication — claude-code opus-5 max | **reward 0** — engineered an input-tampering exploit (rewrote the recording so the verifier would re-project a planted cloud); defeated because the verifier reads its own baked keyframes |
| `/cheat` trial — codex gpt-5.6-sol xhigh | **reward 0** — provider refused the red-team brief (3 attempts) |

The recording (2.92 GB) is not committed; `environment/Dockerfile` downloads it at build time from
the public dataset https://huggingface.co/datasets/pinkman9/aircraft-orbit-mapping and verifies its
SHA-256 (`docs/data_provenance.md`).

## Repository visibility and what publishing it means

This repository is public, which is the same posture as every task merged into Terminal-Bench: the benchmark repo
carries each task's `tests/` and `solution/` directories in the open, and its contributing guide asks only that
solutions not be "easily findable online (besides oracle solutions in this repo)". Publishing has a consequence worth
stating plainly rather than leaving a reader to discover it.

`tests/reference/aircraft_ref.ply` (the ground-truth model the verifier scores against) and `tests/thresholds.json`
(the gates) are committed here. An agent solving the task receives the exact text of `instruction.md`, which also lives
here, so a web search on one sentence of it reaches this repository, and from there the reference model. Registering
raw scans against that model would produce a passing trajectory without doing the work. That exposure cannot be
engineered away while the repository is public: moving the data files elsewhere does not help, because the instruction
itself is the search key. Terminal-Bench addresses this with the canary string (an anti-training-contamination marker,
present in every task file here) and the closing "do not cheat by using online solutions" sentence in the instruction,
not with secrecy.

**The six agent trials in `RESULTS.md` were run while this repository was private**, and the git history timestamps
that: they completed on 2026-09-16 and 2026-09-17, before publication. They therefore measure the task's intrinsic
difficulty, not its resistance to a web search.

**One adversarial trial was then re-run deliberately against the published repository** (`cheat-claude-public`) to test
whether the exposure is exploitable in practice. It is not, on this evidence: the agent made zero web-search and
zero web-fetch calls across 86 tool calls and never referenced this repository. It attacked the verifier's input
instead — rewriting `/app/data/orbit.mcap` so that re-projecting its own delivered poses would reconstruct its
`aircraft.ply` exactly — and the attack reached nothing, because the verifier's raw scans are baked into the verifier
image and the agent container is destroyed before verification begins. Reward 0, caught independently by two gates.
Full account in `CHEAT_ANALYSIS.md`.

The dataset hosting the recording was also rewritten on 2026-09-17 so its card describes only the sensor data, with no
link back here and no indication the recording belongs to a benchmark task.

## Known limitations

Recorded plainly rather than buried:

- **Both trials run under the TB3 red-team brief hit model safety classifiers.** OpenAI's API refused codex
  outright on all three attempts, so that trial never exercised the verifier at all; claude-code ran but had one
  reconnaissance command flagged (`api_refusal_category='cyber'`), forcing a mid-session model fallback. Both scored
  zero and `harbor analyze` records `reward_hacking: pass` for the claude-code probe. A third adversarial trial
  (`cheat-claude-public`) ran cleanly after publication, built a real input-tampering exploit and was defeated by the
  verifier — that run, not the degraded pair, is the strongest anti-cheat evidence here.
- **`harbor analyze` flags `near_miss` on the three trials it analyzed** — all three are superseded Modal runs that harbor
  never scored. The closest *counted* trial missed the trajectory gate by 0.013 (0.707 against 0.72).
  `FAILURE_ANALYSIS.md` quantifies this, explains why the gate still separates the two measured populations cleanly, and
  specifies the metric correction that should be made (and recalibrated from scratch) rather than moving the threshold.
- **The agent image pre-installs a generic point-cloud stack** (numpy, scipy, open3d, mcap). The rubric prefers leaving
  dependency discovery to the agent; this is a deliberate judgement call recorded in `docs/RUBRIC_SELF_REVIEW.md` row 18.

## Author

Siddartha Reddy Chinthala. The ground-truth reference model and the vendored solver patches came from the robot platform's
team and are reused with permission; everything else — task design, tooling, verifier, calibration — is the author's work.
See `docs/data_provenance.md`.

