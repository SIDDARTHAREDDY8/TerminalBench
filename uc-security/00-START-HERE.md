# UC DTS Find-and-Fix — Engagement Workspace

## Rule zero (do this before anything else)
- [ ] Written authorization from supervisor saved (screenshot Slack/email) → put it in `authorization/`
- [ ] Scope confirmed IN WRITING: exact hosts/apps I may test, and what's OFF limits
- [ ] Testing window / rate-limit expectations confirmed (so a scan never causes an outage)

If any box above is unchecked, stop and close it first. Everything below assumes these are done.

---

## The method: MAP → PRIORITIZE → TEST → PROVE → FIX

You "find where to start" by building an asset inventory, scoring each asset, and
attacking the highest value-for-lowest-risk target first. You never start by
randomly poking things.

### Step 1 — MAP (recon). Fill in `recon/inventory.md`.
For each in-scope target, record: URL/host, tech stack, auth type, does it hold
sensitive data (student PII, grades, payment?), is it internet-facing or internal.

Commands (run only against IN-SCOPE hosts):
```
# live hosts from a list
httpx -l recon/scope.txt -title -tech-detect -status-code -o recon/live.txt

# subdomains (only if whole domains are in scope, not single apps)
subfinder -d <in-scope-domain> -o recon/subs.txt

# fingerprint a single app
whatweb https://<target>
```

### Step 2 — PRIORITIZE. Score each asset 1-5 on:
- **Data sensitivity** (PII/grades/payments = 5)
- **Exposure** (public internet = 5, internal-only = 2)
- **Attack surface** (login forms, file upload, search, APIs = higher)
Start with the highest total. That's your answer to "where do I start."

### Step 3 — TEST. Two passes:
**Automated first pass (fast, catches known issues):**
```
# templated vuln scan — THROTTLED so it can't take prod down
nuclei -l recon/live.txt -rl 20 -c 10 -o findings/nuclei.txt
```
**Manual pass (where the real, rewardable bugs live).** Highest-yield classes for
university systems, in order:
1. **Broken access control / IDOR** — change an id in a URL or API call, can you
   see another user's data? Automation misses these; they are the #1 uni finding.
2. **Authentication flaws** — password reset abuse, session handling, missing MFA.
3. **Injection** — SQLi, then XSS.
4. **SSRF / exposed config / secrets in JS or .git**.
Proxy every request through **Burp Suite (Community, free)** so you can see and
modify traffic.

### Step 4 — PROVE (safely).
- Demonstrate impact with the MINIMUM: one record, one screenshot. Then STOP.
- NEVER bulk-download real data. NEVER pivot to a system that isn't in scope.
- Note exact reproduction steps as you go — you won't remember them later.

### Step 5 — FIX (this is find-AND-fix — the fix is half the value).
For each finding write: root cause + the specific code/config change that closes it.
Use `findings/TEMPLATE.md`.

---

## Learn-while-you-do (free, maps 1:1 to the above)
- PortSwigger Web Security Academy — do "Access control" and "SQL injection" labs first.
- OWASP Top 10 (2021) — your checklist of what to look for.
