# Infrastructure failures — re-run, never counted

The assessment excludes agent crashes, API and rate-limit failures, container failures and timeouts from counting as
model failures. Every such failure in this project is listed in `RESULTS.md` with its cause; this directory holds the
machine-readable evidence for the ones that happened on the GCP VM.

| file | what it shows |
|---|---|
| `run-claude-1rerun-quota-*` | harbor `result.json` and the agent's own final line: `You've hit your session limit · resets 5am (UTC)` |
| `run-claude-2rerun-quota-*` | the same failure; the two trials were launched **concurrently**, which exhausted the shared Claude subscription quota. Re-running them one at a time afterwards completed cleanly |
| `run-claude-2rerun-netfail-*` | `NetworkConnectionError` / `Connection timed out` during agent installation, 6 min in; the agent never started and produced no transcript |

The three Modal verifier-build failures (`run-codex-2`, `run-claude-1`, `run-claude-2`) keep their evidence in their own
`docs/runs/<job>/` directories, including `modal_exception_tail.txt` where harbor captured Modal's message.
