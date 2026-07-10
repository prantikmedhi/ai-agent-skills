#!/usr/bin/env python3
"""
vuln_scan.py — heuristic security hotspot scanner.

Walks a codebase and flags lines matching known-risky patterns across the audit
categories (injection, access-control, auth, secrets, database, pii, xss, ssrf/cors,
deserialization, path-traversal, dos, crypto). It is a *grep with judgment*, not a
prover: every hit means "read this and trace the data flow," not "this is a bug."
False positives and misses are expected — the real audit is a human/model reading
the code (see SKILL.md). This just points at the hotspots fast.

Usage:
    python3 vuln_scan.py --path .
    python3 vuln_scan.py --path ./src --json
    python3 vuln_scan.py --path . --category injection,secrets,dos
    python3 vuln_scan.py --path . --min-severity high
    python3 vuln_scan.py --selftest

Exit code: number of findings (capped at 250) so it can gate CI; 0 = clean.
"""
import argparse
import json
import os
import re
import sys

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "__pycache__",
    ".venv", "venv", "env", ".idea", ".vscode", ".mypy_cache", ".pytest_cache",
    "coverage", ".next", ".nuxt", "target", "bin", "obj",
}
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".wav", ".lock",
    ".min.js", ".map", ".so", ".dylib", ".dll", ".class", ".pyc",
}
MAX_BYTES = 2_000_000  # skip files bigger than this; huge files are usually assets

# ponytail: regex heuristics, not taint analysis. High recall, moderate precision —
# upgrade to a real SAST engine (semgrep/CodeQL) only if false-positive rate hurts.
# Each rule: (id, category, severity, regex, hint)
RULES = [
    # --- injection ---
    ("sql-string-concat", "injection", "high",
     r"""(execute|query|cursor\.execute|raw)\s*\(\s*[^)]*(["'`].*(SELECT|INSERT|UPDATE|DELETE|WHERE).*["'`]\s*(\+|%|\.format|\$\{|f["']))""",
     "SQL built by string concat/format — use parameterized queries."),
    ("shell-injection", "injection", "critical",
     r"""(os\.system|subprocess\.(call|run|Popen)\([^)]*shell\s*=\s*True|child_process\.(exec|execSync)|\bexec\()\s*\(?[^)]*(\+|\$\{|%|\.format|f["'])""",
     "Shell command with interpolated input — pass argv array, no shell=True."),
    ("code-eval", "injection", "critical",
     r"""\b(eval|exec)\s*\(""",
     "eval/exec — never on untrusted input; avoid entirely if possible."),
    ("js-eval", "injection", "high",
     r"""\bnew\s+Function\s*\(|\bsetTimeout\s*\(\s*["'`]""",
     "Dynamic code from string — treat as eval; remove."),
    # --- secrets ---
    ("private-key", "secrets", "critical",
     r"""-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----""",
     "Private key committed — rotate immediately, purge from history."),
    ("aws-key", "secrets", "critical",
     r"""\bAKIA[0-9A-Z]{16}\b""",
     "AWS access key id in source — rotate and move to a secret manager."),
    ("generic-secret", "secrets", "high",
     r"""(?i)\b(api[_-]?key|secret|passwd|password|token|access[_-]?key)\b\s*[:=]\s*["'][^"'\s]{8,}["']""",
     "Hardcoded credential — move to env/secret manager, rotate."),
    ("db-conn-string", "database", "high",
     r"""(?i)(mongodb(\+srv)?|postgres(ql)?|mysql|redis|amqp)://[^\s"']*:[^\s"'@]+@""",
     "Connection string with embedded password — externalize and rotate."),
    # --- auth / crypto ---
    ("weak-hash", "crypto", "high",
     r"""(?i)\b(md5|sha1)\s*\(""",
     "MD5/SHA1 for security — use SHA-256+ / bcrypt/argon2 for passwords."),
    ("weak-random-token", "crypto", "medium",
     r"""(?i)(token|secret|password|nonce|salt|session).{0,20}(Math\.random|random\.random|rand\(\))""",
     "Non-CSPRNG for a security value — use secrets/os.urandom/crypto."),
    ("tls-verify-off", "crypto", "high",
     r"""(?i)(verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER.{0,10}(0|false))""",
     "TLS verification disabled — enables MITM; remove."),
    ("jwt-alg-none", "auth", "critical",
     r"""(?i)(alg["']?\s*[:=]\s*["']none["']|algorithm\s*=\s*["']none["'])""",
     "JWT alg=none accepts unsigned tokens — pin a strong algorithm."),
    # --- pii / info leak ---
    ("debug-prod", "pii", "medium",
     r"""(?i)(DEBUG\s*=\s*True|app\.debug\s*=\s*True|FLASK_DEBUG\s*=\s*1)""",
     "Debug mode leaks stack traces/internals — disable in production."),
    # --- xss ---
    ("xss-sink", "xss", "high",
     r"""(?i)(dangerouslySetInnerHTML|\.innerHTML\s*=|v-html|document\.write\s*\(|\|\s*safe\b|mark_safe\s*\()""",
     "Raw HTML sink — encode output / rely on auto-escaping + CSP."),
    # --- ssrf / cors ---
    ("cors-wildcard", "ssrf", "medium",
     r"""(?i)Access-Control-Allow-Origin["'\s:]+\*""",
     "CORS '*' — never with credentials; reflect vetted origins only."),
    # --- deserialization / path traversal ---
    ("insecure-deser", "deserialization", "high",
     r"""(?i)(pickle\.loads|yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.SafeLoader)|cPickle\.loads|marshal\.loads)""",
     "Native deserialization of untrusted data — use JSON / safe_load."),
    ("path-traversal", "path-traversal", "medium",
     r"""(open|readFile|sendFile|include|require)\s*\([^)]*(\.\.\/|\.\.\\|\breq\.(params|query|body)\b[^)]*)\)""",
     "File path from user input — canonicalize and confine under a base dir."),
    # --- dos / resource exhaustion ---
    ("no-limit-query", "dos", "low",
     r"""(?i)\b(find|findall|all|scan|query)\s*\(\s*\)\s*(;|$)""",
     "Unbounded fetch — add LIMIT/pagination to avoid resource exhaustion."),
    ("redos", "dos", "medium",
     r"""\(\.[\*\+]\)[\*\+]|\([^)]+[\*\+]\)[\*\+]""",
     "Nested quantifier regex — possible ReDoS on user input."),
    ("no-timeout-fetch", "dos", "low",
     r"""(?i)(requests\.(get|post|put)\((?![^)]*timeout)|urllib\.request\.urlopen\((?![^)]*timeout))""",
     "Outbound call without timeout — a slow peer can exhaust workers."),
]

COMPILED = [(rid, cat, sev, re.compile(rx), hint) for rid, cat, sev, rx, hint in RULES]
ALL_CATEGORIES = sorted({r[1] for r in RULES})


def _is_binary(path):
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(1024)
    except OSError:
        return True


def scan_file(path):
    findings = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, 1):
                if len(line) > 2000:  # minified/one-line bundle — skip, too noisy
                    continue
                for rid, cat, sev, rx, hint in COMPILED:
                    if rx.search(line):
                        findings.append({
                            "file": path, "line": lineno, "rule": rid,
                            "category": cat, "severity": sev, "hint": hint,
                            "code": line.strip()[:160],
                        })
    except OSError:
        pass
    return findings


def scan_tree(root, categories=None, min_sev="low"):
    min_rank = SEVERITY_ORDER[min_sev]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if any(name.endswith(ext) for ext in SKIP_EXT):
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            if _is_binary(path):
                continue
            for fnd in scan_file(path):
                if categories and fnd["category"] not in categories:
                    continue
                if SEVERITY_ORDER[fnd["severity"]] < min_rank:
                    continue
                out.append(fnd)
    out.sort(key=lambda f: (-SEVERITY_ORDER[f["severity"]], f["file"], f["line"]))
    return out


def _fmt(findings):
    if not findings:
        return "No hotspots found. (Heuristic scan — still read auth/db/admin code by hand.)"
    lines, counts = [], {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    summary = ", ".join(f"{counts[s]} {s}" for s in ("critical", "high", "medium", "low") if s in counts)
    lines.append(f"{len(findings)} hotspot(s): {summary}\n")
    for f in findings:
        lines.append(f"{f['file']}:{f['line']} — [{f['severity'].upper()}] {f['category']}/{f['rule']}")
        lines.append(f"    {f['code']}")
        lines.append(f"    → {f['hint']}")
    return "\n".join(lines)


def _selftest():
    import tempfile
    bad = (
        'API_KEY = "sk_live_abcd1234efgh5678"\n'
        'cursor.execute("SELECT * FROM u WHERE id = " + user_id)\n'
        'import hashlib; hashlib.md5(pw)\n'
        'eval(request.data)\n'
        'requests.get(url)\n'
    )
    good = 'x = 1 + 2  # nothing risky here\nreturn "hello"\n'
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "bad.py"), "w") as f:
            f.write(bad)
        with open(os.path.join(d, "good.py"), "w") as f:
            f.write(good)
        found = scan_tree(d)
        cats = {f["category"] for f in found}
        rules = {f["rule"] for f in found}
        assert "secrets" in cats, "missed hardcoded secret"
        assert "injection" in cats, "missed SQL/eval injection"
        assert "generic-secret" in rules, f"missed generic-secret; got {rules}"
        assert "code-eval" in rules, f"missed eval; got {rules}"
        assert not [f for f in found if f["file"].endswith("good.py")], "false positive on clean file"
        # filters
        assert scan_tree(d, categories={"secrets"}), "category filter dropped everything"
        assert all(f["severity"] in ("critical", "high")
                   for f in scan_tree(d, min_sev="high")), "min-severity leaked lows"
    print("vuln_scan selftest: OK")


def main():
    ap = argparse.ArgumentParser(description="Heuristic security hotspot scanner")
    ap.add_argument("--path", default=".")
    ap.add_argument("--category", help="comma-separated subset: " + ",".join(ALL_CATEGORIES))
    ap.add_argument("--min-severity", default="low", choices=list(SEVERITY_ORDER))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    cats = set(args.category.split(",")) if args.category else None
    findings = scan_tree(args.path, categories=cats, min_sev=args.min_severity)
    print(json.dumps(findings, indent=2) if args.json else _fmt(findings))
    sys.exit(min(len(findings), 250))


if __name__ == "__main__":
    main()
