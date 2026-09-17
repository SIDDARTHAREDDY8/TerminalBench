# FAILURE_ANALYSIS — why the agents fail

Each entry is written from the trial's transcript (`docs/runs/<job>/`), the verifier's per-test diagnostics (`ctrf.json`,
`test-stdout.txt`) and, where available, `harbor analyze`. The question for every trial is the one the TB3 reviewers ask:
did the agent fail on the task's stated difficulty crux, or on something unrelated (specification gap, infrastructure,
formatting)? The task's crux (`tasks/aircraft-orbit-mapping/README.md`): the GNSS-INS pose stream looks trustworthy but its
heading noise over the 17 m lever arm smears every accumulation below the 0.72 local-precision gate; nothing in the
environment can reveal that, because every self-consistency check compares the scans against a map built from the same
poses; and closing the gap needs a scan-matching front-end registering against an *incrementally built* map, driven by
the odometry prior that the URDF sensor transforms make possible.

**A correction the trials forced on this write-up.** Earlier drafts attributed the gap to pose-graph *loop closure*.
The calibration record disproves that: every passing oracle run accepted **zero** loop closures (candidates need 100 m
of accumulated path and the registration scores never reach the threshold) and still scored 0.805–0.813. What separates
the populations is the incremental NDT front-end, not the back-end. The analysis below uses the corrected crux.

## run-codex-1 — codex / gpt-5.6-sol xhigh — reward 0 (crux failure)

**What it did (27 commands, 17 min).** Inventoried `/app/data`, read the MCAP with `mcap_ros2`, and within the first
four commands decided: *"a high-quality GNSS/INS pose stream with centimetre-scale reported covariance. I'll use that
absolute pose as the drift-free backbone, interpolate it at the exact scan stamps, and apply the calibrated
`vrtk_link → base_link` offset."* It wrote `/app/reconstruct.py` (pose interpolation + apron-plane fit + DBSCAN
extraction), built the aircraft by accumulating `/fused_points` with those poses, deskewed the raw Hesai/Livox returns
using per-point timestamps, trimmed them to an 8 cm neighbourhood of the fused-scan seed, and ran a self-consistency
check: *"a held-out-scan check against the reconstructed aircraft gives a median point-to-model residual around 4 cm,
with roughly 87 % of returns within 10 cm before any scan matching. That is comfortably above the requested precision
threshold, so I'm keeping the GNSS/INS poses as the trajectory backbone rather than introducing unstable per-scan ICP
corrections."* It then declared completion.

**What the verifier saw.** `test_files`, `test_consistency` (3 cm / 0.2°) and `test_cleanliness` (0.0 % apron) pass —
the deliverables are well-formed, self-consistent and clean. `test_reaccumulation` fails at local precision **0.684**
(gate 0.72) and `test_aircraft_model` at **0.659** (gate 0.72), with coverage 0.99 on both. 0.684 is, to three decimals,
the value the GNSS-INS trajectory scored during calibration (`docs/CALIBRATION.md`): the agent delivered exactly the
shortcut the task was designed to reject.

**Why the self-check fooled it.** Measuring held-out scans against a model built from the *same* poses only measures
per-scan noise around the smeared surface; the smear itself (heading noise × lever arm, ~24 cm 1σ) is invisible to any
check that does not have an independent reference. The agent had a public, drift-free alternative (scan-matching SLAM
with the URDF transforms and loop closure — ROS 2 Humble and the MCAP plugin were in the image) and explicitly
rejected it as "unstable". It also never used `/tf`, the URDF beyond the one lever-arm offset, or the wheel odometry.

**Verdict.** Genuine failure on the crux, not a near miss in the calibration sense: the gap to the gate (0.036) equals
the gap between the shortcut population and the SLAM population, and the model test is farther off (0.659). Not a
specification problem — every gate and format was met except the two accuracy gates the instruction states.

**`harbor analyze` (trial-analysis rubric, claude-sonnet-5; `docs/runs/run-codex-1/analysis.json`).** task_specification
pass ("instructions were unambiguous and fully actionable"); reward_hacking pass (no probing for tests/solution, no
hardcoding); difficulty_crux pass ("exactly the crux the task was designed around… landing at 0.684/0.659 — almost
identical to the documented naive-baseline score of 0.68"); near_miss pass ("not a threshold-calibration issue: the
agent's approach is the specific shortcut baseline… the gate is correctly discriminating"); refusals n/a; low_timeout
pass (17 min of a 4 h budget used). Analysis cost $0.30.

## run-codex-2 — codex / gpt-5.6-sol xhigh — reward 0 (crux failure; model gate passed, trajectory gate not)

**What it did (34 commands, 20 min).** Same opening decision as trial 1, reached even faster: *"The dataset includes a
10 Hz GNSS/INS pose stream, so the fixed-world trajectory can be obtained without accumulating wheel-odometry drift."*
It cross-checked the odometry topic against the recorded `map → odom → vrtk_link` TF chain ("agree to numerical
precision" — true, they are the same sensor), fitted the apron plane from the robot footprint, and then invested the
rest of its effort in the *model*: a 4 cm voxel accumulation, a repeated-view support filter ("half the voxels occur in
only one scan, while the aircraft surfaces are repeatedly observed"), 3-D connected components, and a de-skewed
raw-sensor reconstruction using per-point timestamps, ending with a 640 k-point single component of 27.1 × 28.8 × 7.1 m.

**What the verifier saw.** Trajectory local precision **0.684** again — the GNSS-INS number — so `test_reaccumulation`
fails; but `test_aircraft_model` passes at 0.737 / 0.955 with junk 0.06, and consistency (4 cm / 0.1°) and cleanliness
(0.0 %) pass. 4/5.

**Why it matters.** Trial 2 shows what heavy post-processing of the *model* can buy without fixing the *poses*: the
multi-view support filter and de-skewing removed enough of the smear's outliers to lift the model's local precision
from 0.659 (trial 1) to 0.737, 0.017 above the model gate. The trajectory gate is the one that cannot be cleaned
around — the raw keyframes re-projected with the agent's own poses carry the full heading-noise smear — and it held at
exactly the shortcut's value. Design note for hardening: the model gate's margin against model-only cleaning is thin
(0.72 vs 0.737); the re-accumulation gate is the load-bearing one and should stay.

**Verdict.** Genuine crux failure: no scan matching, no loop closure, GNSS-INS poses delivered as the trajectory.

## run-codex-3 — codex / gpt-5.6-sol xhigh (GCP VM, docker backend) — reward 0 (crux failure)

**What it did (15 min).** Third time the same fork in the road, taken the same way: *"The recording contains a strong
absolute solution: 10 Hz GNSS–INS poses plus the missing rigid `vrtk_link → base_link` calibration. That should give
the required metric, drift-free trajectory without relying on scan-matching drift."* It even framed the right question —
*"whether GNSS–INS vertical and heading consistency are already within the surface tolerances or need scan-based
refinement"* — and answered it from internal coherence only ("the first globally transformed sample is internally
coherent"), which cannot see the smear. The rest of the run was model hygiene: temporal-persistence filtering, a
4 cm-voxel accumulation, removal of a low return ahead of the nose ("tug or ground-support equipment").

**What the verifier saw.** Trajectory local precision **0.684** (gate 0.72) → `test_reaccumulation` fails; model
0.773 / 0.966, junk 0.04, consistency 2 cm / 0.04°, apron 0.0 % → the other four pass.

**Pattern across the three codex trials.** Identical trajectory score (0.684, the GNSS-INS baseline) three times;
model score rising 0.659 → 0.737 → 0.773 as each run cleaned harder. Every run declared itself done inside 20 minutes
of a 4-hour budget after a self-check that used its own poses as ground truth. None ran an incremental scan-matching front-end or used the wheel odometry; none installed or built anything. The failure is the task's stated crux, reproduced 3/3.

**`harbor analyze` on codex trials 2 and 3** (`docs/runs/run-codex-2/analysis.json`, `run-codex-3/analysis.json`).
Trial 3: all six checks pass (difficulty_crux: "lands exactly on the crux the task was designed around"; near_miss:
"the agent landing squarely on the documented naive-baseline population (0.68) rather than partially succeeding at the
reference SLAM approach (0.80–0.81)"). Trial 2: five pass, **near_miss fail** — the analyzer noted that the trajectory
missed its gate by 0.036 while the model cleared the same 0.72 bar by only 0.017 and read that clustering as a possible
calibration issue.

On that flag: the trajectory score is not near the gate by accident — 0.684 is the GNSS-INS baseline to three decimals
in all three trials and in the calibration record, and the gate was placed between that population (≤ 0.68) and the
SLAM population (0.80–0.81); no amount of model cleaning moves it, because the re-accumulation uses the agent's poses
on raw keyframes. The thin margin is on the *model* gate: heavy filtering of a GNSS-accumulated cloud reached 0.737 and
0.773 against the same 0.72 bar. Since the model gate is a secondary check (the trajectory gate already decides these
trials) and because retuning thresholds after watching agents would be exactly the adversarial calibration the TB3
guide warns against, the thresholds were left as calibrated. A future revision could raise the model gate to ~0.76
(reference solution 0.80–0.81 on five runs) to restore a symmetric margin; this is recorded here as a known design
observation, not applied.

## run-claude-1 — claude-code / opus-5 max — reward 0 (near miss: 0.7138 vs the 0.72 gate)

**What it did (~2 h).** The only trial so far to engage the crux. It reverse-engineered `/fused_points` as a raw
concatenation (Hesai block matching `/hesai/points` through the URDF `base_link→hesai` transform "to 1e-7 m", then four
Livox blocks), reconstructed a per-point timestamp for all 152 k points, and motion-compensated them — noting the robot
rotates up to 50 °/s so "intra-scan smear reaches ~1 m at 15 m range". It then took the GNSS-INS + URDF pose as an
*initial* trajectory and refined it with three passes of motion-compensated scan-to-map point-to-plane ICP against a
voxel-mean map (observing that a first-point map "self-attracts and stalls"), converging at 3 mm / 0.008°, and optimised
a per-scan time shift (median 0.044 s) because the scans are not deskewed.

**What the verifier saw.** Trajectory local precision **0.7138** — 0.006 below the gate, and 0.03 above the
GNSS-INS baseline that all three codex trials produced, so the ICP refinement did measurably improve the poses.
Model 0.760 / 0.970, junk 0.048, consistency 1.6 cm / 0.03°, apron 0.0 %: 4/5 tests pass.

**The agent diagnosed its own margin.** Without access to the reference it built a proxy and reported: aircraft-surface
points score 0.87–0.90 at 0.10 m, but "~25 % of the points within 1.0 m of the reference are *apron* points in the halo
under the landing gear, which score 0 by construction… the graded value could land either side of 0.72". That is an
accurate reading of the metric: `localprec`'s denominator is every re-accumulated point within `junk_radius_m` (1.0 m)
of the reference, and the hidden reference's lowest surface sits 0.47 m above the apron, so ground returns beneath the
aircraft fall inside that radius and count against the score no matter how good the poses are.

**Verdict and caveat.** A genuine failure on the crux — the trajectory is still not drift-free enough — but a *near
miss*, and by TB3's own definition (`near_miss`: "agents are reaching substantively working solutions and being
defeated by the verifier's threshold rather than the conceptual challenge") this one trial is close enough to warrant
the flag. See "Threshold margin" below once all claude trials are in.

## run-claude-2 — claude-code / opus-5 max — reward 0 (crux failure)

**What it did (~2 h, 35 shell commands).** A different and more ambitious attack than trial 1: it wrote its own
refinement stack (`core.py`, `refine.py`, `ground2.py`, `sharp.py`) and ran *six* successive rounds of pose refinement
(`poses_c3 → c4 → c5 → c6`), each seeded from the previous and each re-estimating a **Livox extrinsic calibration**
(`livox_calib_v3/v4.npz`) alongside the poses. It also built an unbiased "map sharpness" objective — occupied voxel
count for a fixed point set — to decide whether each round actually improved the map, which is the right instinct for a
problem where no ground truth is available.

**What the verifier saw.** Trajectory local precision **0.689** (gate 0.72), model 0.722 / 0.968, junk 0.06,
consistency 2.5 cm / 0.01°, apron 0.0 %. 4/5 tests pass. Its model is the largest submitted (1.25 M points) and its
model score (0.7221) clears the model gate by 0.002.

**Why it still fails.** Six rounds of self-consistent refinement optimise the map against itself. Sharpness rises as
scans agree with each other, which a globally smeared-but-locally-consistent solution can achieve; only registration against a map built
incrementally from already-placed scans — what the reference front-end does — avoids folding the initial bias into the
target it is matching against. It ended 0.025 below trial 1, which used fewer but better-posed ICP passes, so more iterations of a
self-referential objective did not help.

**Verdict.** Genuine crux failure, no near-miss flag (0.031 below the gate).

## run-claude-3 — claude-code / opus-5 max (GCP VM, docker backend) — reward 0 (crux failure, self-validation gave a false negative)

**What it did (~1 h 40 m).** It used the same GNSS-INS + URDF pose chain, but unlike the other two opus trials it
explicitly *tested* whether refinement was needed — and concluded it was not. In its own words: it built a 6.1 M-point
voxel map, ran point-to-plane ICP per scan against it, found "corrections… at **3–5 mm and ~0.01°** with zero
systematic bias" and a median residual of 0.017 m, and concluded "the GNSS-INS poses are already ground-truth quality,
so refining them would only fit noise". It went further and claimed global closure: "start-vs-end overlap (scans 0–140
vs 1320–1462) matches as well as time-adjacent scans, confirming drift-free closure". It then spent the remaining time
on the model, fighting "mixed-pixel artifacts — a 'starburst' fan radiating from silhouette edges".

**What the verifier saw.** Trajectory local precision **0.685** — the GNSS-INS baseline, and 0.029 *below* trial 1,
which did refine. Model 0.573 (worst of all six trials; it kept 948 k points including the artifacts it had been
fighting). 3/5 tests pass.

**Why its validation was wrong.** The ICP corrections were measured against a map accumulated *with the poses under
test*. A trajectory that is smoothly and consistently wrong produces a map that is smoothly and consistently wrong, and
every scan then agrees with it to millimetres. The same applies to the start/end overlap check: both ends were placed by
the same GNSS-INS solution, so their agreement measures the sensor's short-term repeatability, not global drift. This is
the sharpest demonstration in the whole trial set of the task's central claim — *without an external reference, a
plausible self-check cannot see this error* — and it is exactly why the reference solution registers against an
incrementally assembled map rather than refining against one pre-built from the poses under test.

**One misreading worth noting.** The agent repeatedly described the LiDAR as "simulated". The recording is real sensor
data; nothing in the environment says otherwise. It did not change the outcome, but it shows the agent building an
incorrect mental model of the data and then trusting artifacts it attributed to simulation.

**Verdict.** Genuine crux failure; no near-miss (0.035 below the gate on the trajectory, 0.147 below on the model).

# Threshold margin and the `near_miss` flag — an honest assessment

`harbor analyze` marks `near_miss` **fail** on both completed opus-5 trials (0.714 and 0.689 against P1 = 0.72), with
"the P1=0.72 threshold may be miscalibrated relative to what a well-executed solution can realistically achieve". TB3's
own guidance says that when multiple trials fail this check, the task may look harder than it is. That flag deserves a
direct answer rather than a threshold edit, so here is the full picture.

## Where every measured trajectory actually lands

| trajectory | local precision @ 0.10 m |
|---|---|
| reference solution (5 runs: 3 Modal, 2 Docker) | 0.805 – 0.813 |
| **P1 gate** | **0.72** |
| opus-5 trial 1 — GNSS-INS + 3× motion-compensated scan-to-map ICP | 0.714 |
| opus-5 trial 2 — GNSS-INS + 6 refinement rounds + Livox self-calibration | 0.689 |
| GNSS-INS + lightweight pose graph (author baseline) | 0.66 |
| gpt-5.6-sol trials 1–3 — GNSS-INS poses, no refinement | 0.684 (×3) |
| GNSS-INS + per-frame ICP refine (author baseline) | 0.57 |

Two facts matter. First, the gate separates the two populations it was built to separate: every non-SLAM trajectory
measured — six agent trials and four author baselines — lands at or below 0.714, and every loop-closed SLAM run lands at
or above 0.805. There is no overlap. Second, the gate sits 0.036 above the naive baseline but 0.09 below the reference
solution: it is placed nearer the failure population than the success population, which is why a strong non-SLAM run can
approach it.

## Is 0.714 "a substantively working solution"?

Partly. Trial 1's refinement is real work and real improvement: +0.030 over the unrefined GNSS-INS poses, about a third
of the distance from the baseline to the reference. But it is not the solution the task asks for. It refines *against a map pre-built from the
GNSS poses*, so the smear is already in the target and ICP converges into it; its own sharpness/consistency checks are
self-referential and cannot observe the residual; and it remains 0.09 short of what the reference pipeline achieves on
the same data by registering each scan against a map assembled only from scans already placed. The
verdict "conceptually beyond reach" is not what the numbers say — the numbers say the agent got most of the way with
local refinement and did not do the one thing (global loop closure) that closes the rest.

## The real weakness the agent found — a metric artifact, not a threshold error

Trial 1 identified something the calibration did not: `localprec`'s denominator is every re-accumulated point within
`junk_radius_m` = 1.0 m of the reference, and the hidden reference's lowest surface is 0.468 m above the apron.
Ground returns in the halo under the fuselage and landing gear therefore fall inside that radius and score 0 no matter
how good the poses are. The agent measured this as roughly 25 % of its in-radius points and correctly predicted the
result could "land either side of 0.72". This compresses every trajectory's score toward a floor set by scene geometry
rather than pose quality, and it is the most likely reason the populations sit closer together than they should.

## What was changed: nothing

No threshold was touched after the trials began. Retuning gates after watching agents is exactly the adversarial
calibration CONTRIBUTING.md warns against, and it would invalidate the calibration record. The thresholds in
`tests/thresholds.json` are the ones fixed before the first trial ran.

## What a revision should do instead

Fix the metric, then recalibrate from scratch — do not move the number:

1. Exclude points below the reference's lowest surface (or below the apron plane + 0.30 m) from `localprec`'s
   denominator, so the score measures aircraft-surface sharpness rather than the halo fraction. All measured
   trajectories would then be rescored and P1 re-derived as the midpoint of the two populations.
2. Re-run the reference solution and all shortcut baselines under the corrected metric before fixing any gate.
3. Expected effect: both populations rise, the SLAM/non-SLAM separation widens, and the gate can sit midway rather
   than 0.036 above the failure population.

Until that recalibration is done, the honest statement is the one this section makes: the gate discriminates correctly
on every trajectory measured so far, and the 0.006 margin on one trial is a real fragility of the current metric.
