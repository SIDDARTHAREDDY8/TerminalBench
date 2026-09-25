# Implementation-rubric self-review — aircraft-orbit-mapping

Manual pass over every criterion in `tb3/docs/prompts/task-implementation.toml` (35 criteria, revision of
2026-09-11), done before the automated `harbor exec` reviewer run recorded in `CHECKS.md`. Outcome of the automated review after the
fixes it prompted: 32 pass / 0 fail / 3 n/a (the reviewer also marked `artifact_efficiency` n/a). "Evidence" points at the
file that a reviewer should open.

| # | criterion | self-verdict | evidence / note |
|---|---|---|---|
| 1 | verifiable | pass | `tests/test.sh` runs pytest with CTRF; pure numpy/scipy, seeded RNG, no network, no LLM judge; 4 min 23 s under emulation (timeout 900 s) |
| 2 | solvable | pass | `solution/solve.sh` passes 5/5 (`docs/runs/2026-09-16-mac-docker/ctrf.json`); an expert who knows the approach needs the ~5 h in `expert_time_estimate_hours` |
| 3 | difficult | pass | featureless apron, smooth fuselage, missing sensor TFs, GNSS heading × lever arm; every measured shortcut fails (`docs/CALIBRATION.md`) |
| 4 | interesting | pass | inspection-grade aircraft models from a robot orbit are paid work at airports / MROs |
| 5 | outcome_verified | pass | instruction states deliverables and metrics only; any SLAM / any tooling is allowed |
| 6 | anti_cheat_robustness | pass, see note | reference model + keyframes live only in the verifier image; agent image holds bag + URDF + README. **Note:** the repository is public and contains `tests/reference/*`. That exposure is deliberate, argued in `README.md`
("Repository visibility") and measured by the `cheat-claude-public` trial in `CHEAT_ANALYSIS.md` |
| 7 | task_security | pass | no exfiltration, no obfuscation; the only network calls are apt/pip/rosdep in `solve.sh` and the bag download at image build |
| 8 | functional_verification | pass | geometry metrics on parsed outputs; no string matching |
| 9 | deterministic_reproducible | pass, see note | verifier deterministic (seeded); pip pins everywhere; apt unpinned by rule. **Note:** the oracle's SLAM is timing-sensitive (bag replay); repeated oracle runs on the CI backend are recorded in `CHECKS.md` |
| 10 | essential_difficulty | pass | formats are trivial (TUM, xyz PLY); failures come from drift / contamination, not formatting |
| 11 | test_instruction_alignment | pass | every gate (95 % stamps, 0.72 / 0.90, 30 %, 2 % at 0.15 m, 0.5 m / 3°) is stated in `instruction.md`; `test_outputs.py` is 208 lines, mostly docstrings + diagnostics |
| 12 | novel | pass | private recording; nothing about this apron / robot / aircraft exists online; lidarslam_ros2 is public but the difficulty is configuring it correctly on this data |
| 13 | agentic | pass | must explore the bag, connect the TF tree via the URDF, build and tune a SLAM stack, iterate on extraction |
| 14 | reviewable | pass | `README.md` explains difficulty / solution / verification; thresholds derived from measured runs, not hardcoded guesses (`docs/CALIBRATION.md`) |
| 15 | instruction_concision | pass | absolute paths, backticks, no headings, no tool list, no method hints; 446 words |
| 16 | solution_quality | pass | full computation at solve time (colcon build + SLAM + extraction); nothing precomputed |
| 17 | separate_verifier_configured | pass | inputs = 2 declared artifacts + `/tests/*`; tooling baked in `tests/Dockerfile`; no duplicated assets between the two images |
| 18 | environment_hygiene | pass, judgment call | agent image installs numpy/scipy/open3d/mcap (generic point-cloud tooling, also used by the reference solution). Alternative: drop them and let `solve.sh` install its own — would need a rebuild; left as is |
| 19 | structured_data_schema | pass | TUM line format and PLY element/properties spelled out in `instruction.md` |
| 20 | typos | pass | paths and names cross-checked by `check-test-file-references` |
| 21 | difficulty_explanation_quality | pass | covers humans and agents, data provenance, who does this job; no pass rates |
| 22 | solution_explanation_quality | pass | matches `solve.sh` step for step |
| 23 | verification_explanation_quality | pass | calibration of every bound justified with measured numbers |
| 24 | category_and_tags | pass | Science / Robotics; tags lidar, slam, point-cloud, ros2, sensor-fusion |
| 25 | task_name | pass | `aircraft-orbit-mapping`, 3 tokens |
| 26 | resource_configuration | pass | 4 cpu / 16 GB / 40 GB for a 3 GB bag + PCL build; agent 4 h, verifier 15 min, build 1 h |
| 27 | task_readme | pass | the four required sections plus a calibration record that exists nowhere else |
| 28 | expert_time_estimate | pass | 5 h |
| 29 | task_toml_schema | pass | only recognised fields |
| 30 | no_extraneous_files | pass | every file is COPY'd, run by `solve.sh`, or read by the tests |
| 31 | artifact_efficiency | pass | artifacts are the two deliverables (~1.7 MB) |
| 32 | verifier_execution_isolation | n/a | verifier never executes agent code |
| 33 | ctrf_reporting | pass | `/logs/verifier/ctrf.json`, 5 tests |
| 34 | do_not_modify_enforced | n/a | no protected-artifact constraint in the instruction |
| 35 | binary_reward | pass | `test.sh` writes exactly `0` or `1` from pytest status + CTRF consistency |
