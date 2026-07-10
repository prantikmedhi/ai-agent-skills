# Codebase Security Audit

Find security vulnerabilities in a codebase and **fix them at the root cause**. A
defensive audit skill for Claude — recon the attack surface, scan for hotspots, confirm
by tracing data flow, patch, and verify.

## Coverage

| Area | What it catches |
|------|-----------------|
| **Injection** | SQL / NoSQL / OS-command / LDAP / SSTI, `eval`/`exec`, `shell=True` |
| **Access control / admin** | unauth admin routes, missing server-side authz, IDOR, mass-assignment, default creds |
| **Auth & sessions / user data** | weak/plaintext password hashing, JWT `alg:none`, weak tokens, PII leakage |
| **Secrets** | API keys, private keys, AWS creds, DB connection strings in source |
| **Database** | string-built queries, embedded passwords, unbounded result sets, missing row authz |
| **XSS / SSRF / CSRF / CORS** | raw HTML sinks, user-controlled fetch, wildcard CORS, missing headers |
| **Deserialization / path traversal / upload** | `pickle`/`yaml.load`, `../`, unvalidated files |
| **DoS / DDoS resilience** | missing rate limits, unbounded input, ReDoS, no timeouts, no query LIMIT |
| **Crypto** | MD5/SHA1, `Math.random()` tokens, disabled TLS verification |
| **Dependencies** | known-vulnerable manifest versions |

## Install

**Claude Code — plugin marketplace:**

```
/plugin marketplace add prantikmedhi/ai-agent-skills
/plugin install codebase-security-audit@ai-agent-skills
```

**Claude Code — script:**

```bash
git clone https://github.com/prantikmedhi/ai-agent-skills.git
cd ai-agent-skills && ./install.sh
```

**Claude Desktop / claude.ai:** `./install.sh --zip`, then upload
`dist/codebase-security-audit.zip` in **Settings → Capabilities → Skills**.

## Use

Just type `/`:

```
/security-audit .
/security-audit ./backend
```

Or ask in plain language — "security-audit this repo", "check my auth code for holes",
"find exposed secrets", "is this endpoint DDoS-resilient" — and the skill triggers.

### The scanner directly

```bash
python3 skills/codebase-security-audit/scripts/vuln_scan.py --path . --json
python3 skills/codebase-security-audit/scripts/vuln_scan.py --path ./src --min-severity high
python3 skills/codebase-security-audit/scripts/vuln_scan.py --path . --category injection,secrets,dos
```

Stdlib-only Python 3, no dependencies. Exit code = number of findings (gates CI).
`--selftest` verifies the rule engine.

## How it works

Five phases (see [SKILL.md](skills/codebase-security-audit/SKILL.md)): **Recon →
Scan → Triage → Fix → Verify**. The scanner is a fast heuristic grep that surfaces
hotspots; the actual judgment — is untrusted input reachable, what's the impact, where's
the root-cause fix — is Claude reading the code with the
[vulnerability catalog](skills/codebase-security-audit/references/vuln_catalog.md).

## Scope & ethics

Audit only code you own or are authorized to test. This skill reports and patches — it
does **not** build working exploits, backdoors, or exfiltration tooling. Live exposed
secrets/PII get flagged for rotation and containment first.

## License

MIT
