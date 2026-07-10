---
name: codebase-security-audit
triggers: [security audit, vulnerability, vulnerabilities, audit, sql injection, xss, ssrf, csrf, idor, exposed secrets, hardcoded secrets, harden, ddos, denial of service, rate limit, broken access control, insecure, owasp, pentest, secure my, check security, find vulnerabilities]
description: >-
  Audit a codebase for security vulnerabilities and fix them. Covers injection (SQL,
  command, LDAP, NoSQL), XSS, SSRF, CSRF, IDOR/broken access control, authn/session
  weaknesses, secrets in code, database exposure (connection strings, unparameterized
  queries, backups), admin-panel exposure and default credentials, PII/user-data
  leakage, insecure deserialization, path traversal, SSTI, weak crypto, missing
  security headers, permissive CORS, vulnerable dependencies, and denial-of-service /
  resource-exhaustion (missing rate limits, unbounded input, no timeouts). Runs a
  recon → scan → triage → fix → verify workflow with a severity model and root-cause
  fixes. Use when the user asks to security-audit / find vulnerabilities / harden a
  codebase, review auth or database or admin code for holes, check for exposed
  secrets or PII, assess DDoS resilience, or fix a specific vulnerability class.
---

# Codebase Security Audit

Systematically find security vulnerabilities in a codebase and fix them at the root
cause. This is **defensive**: audit code you are authorized to work on, report findings
plainly, and patch them. It is not for building attacks — never weaponize a finding
beyond a minimal proof needed to confirm it.

Work the five phases in order. Don't jump to fixes before recon and triage — a patch on
the wrong layer leaves sibling call sites exploitable.

---

## Phase 1 — Recon (understand before you scan)

Map the attack surface first:

1. **Stack & entry points.** Language(s), framework(s), how requests enter (HTTP routes,
   GraphQL, gRPC, CLI, queue consumers, webhooks). Read the router/URL config.
2. **Trust boundaries.** Where does untrusted input cross into the system — request
   bodies/params/headers, file uploads, third-party webhooks, message queues, env,
   deserialized data? Every boundary is a candidate.
3. **Sensitive assets.** Where do secrets, credentials, PII, payment data, and auth
   tokens live and flow? Find the DB layer, the auth layer, the admin surface.
4. **Dependencies.** Note the manifest(s) (`package.json`, `requirements.txt`, `go.mod`,
   `pom.xml`, `Gemfile`, `composer.json`) — dependency CVEs are in scope.

Read `references/vuln_catalog.md` for the full category checklist and per-class fixes.

## Phase 2 — Scan (breadth, then depth)

Run the accelerator to surface hotspots, then read the code around each hit:

```bash
python3 scripts/vuln_scan.py --path . --json
python3 scripts/vuln_scan.py --path . --category injection,secrets,dos
python3 scripts/vuln_scan.py --path ./src --min-severity high
```

The scanner is a **heuristic grep** — it points you at risky patterns (raw SQL string
building, `eval`, `child_process` with interpolation, hardcoded keys, missing rate
limits). It has false positives and misses logic bugs. Treat every hit as *"read this,"*
not *"this is a bug."* Confirm by reading the code and tracing the data flow from an
untrusted source to the sink.

Cover the categories the user named plus the rest of the catalog:

- **Injection** — SQL/NoSQL/OS-command/LDAP/SSTI: untrusted input reaching an
  interpreter without parameterization/escaping.
- **Database** — string-built queries, exposed connection strings, over-broad DB
  accounts, world-readable backups/dumps, missing row-level authz.
- **Broken access control / admin side** — unauthenticated admin routes, missing
  server-side authz checks, IDOR (object id from request trusted without ownership
  check), default/hardcoded admin credentials, mass-assignment.
- **AuthN & sessions / user data** — weak or absent password hashing (plaintext, MD5,
  SHA1, unsalted), predictable tokens, missing session expiry/rotation, PII in logs or
  responses, verbose error leakage.
- **SSRF / CSRF / CORS / headers** — server-side fetch of user-controlled URLs, missing
  CSRF protection on state-changing routes, `Access-Control-Allow-Origin: *` with
  credentials, missing `Content-Security-Policy`/`HSTS`/`X-Content-Type-Options`.
- **Secrets** — API keys, passwords, private keys, tokens committed in code, config, or
  git history.
- **Deserialization / path traversal / file upload** — untrusted `pickle`/`yaml.load`/
  Java deserialization, `../` in file paths, unvalidated upload type/size.
- **DoS / resource exhaustion** — no rate limiting on expensive/auth endpoints, unbounded
  request bodies or uploads, no query `LIMIT`, catastrophic-backtracking regex (ReDoS),
  missing timeouts on outbound calls, unbounded recursion/loops on user input.
- **Crypto** — weak algorithms, ECB mode, static IVs, `Math.random()` for tokens,
  disabled TLS verification.
- **Dependencies** — known-vulnerable versions in the manifest.

## Phase 3 — Triage (severity + exploitability)

For each confirmed finding, assign severity by **impact × exploitability**:

- **Critical** — remote code execution, auth bypass, full DB read/write, secret
  exfiltration, unauthenticated admin access.
- **High** — SQLi/stored XSS with real data reach, IDOR exposing other users' data,
  privilege escalation, DoS that takes the service down.
- **Medium** — reflected XSS, CSRF on meaningful actions, missing security headers with
  a real vector, verbose error leakage of internals.
- **Low** — defense-in-depth gaps, best-practice deviations without a direct exploit.

Drop findings you can't tie to a concrete failure path — a scanner hit with no reachable
untrusted-input flow is noise, not a bug. State inputs → sink → impact for each real one.

## Phase 4 — Fix (root cause, minimal diff)

Fix where all callers route through, not per-symptom:

- **Injection** → parameterized queries / prepared statements / safe ORM APIs; never
  string-concatenate untrusted input into a query or shell. Allow-list, don't blocklist.
- **Access control** → enforce authz **server-side** on every protected route; check
  object ownership, not just authentication. Deny by default.
- **Secrets** → move to env/secret manager, rotate the exposed value, purge from git
  history. Never just delete the line — a committed secret is already compromised.
- **Passwords** → `bcrypt`/`argon2`/`scrypt` with per-user salt; never MD5/SHA1/plaintext.
- **XSS** → context-aware output encoding + CSP; prefer framework auto-escaping.
- **SSRF** → allow-list destinations, block internal IP ranges, no user-controlled host.
- **DoS** → rate-limit at the gateway/app, cap body/upload size, add query `LIMIT` and
  outbound timeouts, replace catastrophic regex. Leave the limit as a tunable constant.
- **Dependencies** → bump to a patched version; if none, isolate or replace.

When you touch a shared function, grep every caller first (the ponytail rule): one guard
in the shared sink beats a guard in each caller and fixes siblings the report didn't name.
Preserve input validation and error handling — never simplify a security control away.

## Phase 5 — Verify (prove the fix)

A fix is not done until you've shown it works:

- Re-run `vuln_scan.py` on the changed paths; the hit should be gone (or explained).
- Add or run a test that exercises the vulnerable path with a malicious input and asserts
  it's now rejected/escaped/limited — the smallest check that fails if the fix regresses.
- Re-read the fixed code to confirm no new call path bypasses the guard.
- Confirm you didn't break the legitimate path.

---

## Reporting

Lead with the outcome: counts by severity and the must-fix-now items. Then per finding:
`file:line — [SEVERITY] category: what's wrong → how to trigger → the fix`. Prose over
scaffolding; group by severity, most severe first. If nothing critical/high was found,
say so plainly rather than inflating lows to look thorough.

## Scope & ethics

Only audit code the user owns or is authorized to test. Report and fix — do not build
working exploits, backdoors, or data-exfiltration tooling from what you find. If a
finding involves live exposed secrets or user data, flag it for rotation/containment
first, before anything else.
