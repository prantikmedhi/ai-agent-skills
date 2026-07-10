---
description: Security-audit a codebase for vulnerabilities and fix them (recon → scan → triage → fix → verify)
allowed-tools: Bash(python3:*), Read, Grep, Glob, Edit
---
Run the codebase security audit defined in
`${CLAUDE_PLUGIN_ROOT}/skills/codebase-security-audit/SKILL.md`. Follow all five phases:

1. **Recon** — map the stack, entry points, trust boundaries, and sensitive assets.
2. **Scan** — run the hotspot scanner, then read the code around each hit:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/codebase-security-audit/scripts/vuln_scan.py" --path <target> --json
   ```
3. **Triage** — confirm each hit by tracing untrusted input → sink; assign severity;
   drop unreachable noise.
4. **Fix** — patch confirmed findings at the root cause (shared sink, not per caller),
   preserving validation and error handling.
5. **Verify** — re-scan, add/run a test with malicious input, confirm the legit path still works.

Consult `${CLAUDE_PLUGIN_ROOT}/skills/codebase-security-audit/references/vuln_catalog.md`
for per-class patterns and fixes. Report outcome-first: counts by severity, then each
finding as `file:line — [SEVERITY] category: problem → trigger → fix`.

Defensive only — audit and patch, do not build working exploits. Target/scope: $ARGUMENTS
