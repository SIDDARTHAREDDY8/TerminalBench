# aircraft-orbit-mapping — a Terminal-Bench 3 task

Take-home for the Klavis AI Founding Engineer role: one original
[Terminal-Bench 3](https://github.com/harbor-framework/terminal-bench-3) task, built to the
current TB3 CI (static checks, implementation rubric, Docker build, oracle/nop validation,
`/run` and `/cheat` trials).

**Status: work in progress** — verifier, oracle solution and environment are implemented and
calibrated natively; Docker validation, agent trials and the hand-written instruction/README
sections are still to come. See "Progress" below.

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
tasks/aircraft-orbit-mapping/   the TB3 task (task.toml, environment/, solution/, tests/)
docs/superpowers/specs/         design spec
docs/instruction_facts.md       fact sheet the hand-written instruction.md is built from
docs/CALIBRATION.md             measured oracle / baseline numbers behind the thresholds
docs/data_provenance.md         how orbit.mcap and the reference data were produced
docs/HANDOFF_MAC.md             step-by-step plan for the remaining (Docker / trial) phase
tools/                          data-prep tooling and the verifier unit tests
```

## Progress

| Gate | Status |
|---|---|
| 22 TB3 static checks | pass (run locally against `scripts/checks/`) |
| Oracle through the verifier | pass 5/5 (native lidarslam run; Docker run pending) |
| GNSS-INS shortcut / nop | reward 0 |
| Verifier unit tests | 27/27 (`tools/calibration/test_verify_lib.py`) |
| Task data published | done — HF dataset `pinkman9/aircraft-orbit-mapping`, hash pinned in the Dockerfile |
| Implementation rubric (`harbor check`) | pending |
| Docker build, oracle, nop (`harbor run`) | pending |
| `/run` trials (3× opus-5 max, 3× gpt-5.6-sol xhigh) | pending |
| `/cheat` trials (1× each) | pending |
| `instruction.md`, README sections (human-written) | pending |

The recording (2.92 GB) is not committed; `environment/Dockerfile` downloads it at build time from
the public dataset https://huggingface.co/datasets/pinkman9/aircraft-orbit-mapping and verifies its
SHA-256 (`docs/data_provenance.md`).

## Author

Siddartha Reddy Chinthala.

