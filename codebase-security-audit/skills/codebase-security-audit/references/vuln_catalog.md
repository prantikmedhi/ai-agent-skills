# Vulnerability Catalog — patterns, why they're dangerous, how to fix

Reference for the audit. Each class lists what to grep/read for, the failure it causes,
and the root-cause fix. Ordered roughly by how often it's exploited. This is the "what to
look for and what to do" companion to `SKILL.md`.

---

## 1. Injection (SQL / NoSQL / OS command / LDAP / SSTI)

**Look for:** untrusted input concatenated or interpolated into a query, shell command,
or template. Red flags: `"SELECT ... " + var`, f-strings/`%`/`.format()` inside SQL,
`cursor.execute("... %s" % x)`, `child_process.exec("cmd " + input)`, `os.system`,
`subprocess(..., shell=True)` with interpolation, `eval` / `exec` / `Function()` on
input, template render with raw user string, Mongo `$where` with input.

**Impact:** data theft/modification, auth bypass, remote code execution.

**Fix:** parameterized queries / prepared statements; safe ORM query builders; pass argv
arrays to subprocess (no `shell=True`); never `eval` untrusted input; allow-list any value
that must reach an interpreter. Escaping is a fallback to parameterization, not a
replacement.

## 2. Broken access control (incl. admin side & IDOR)

**Look for:** routes that change state or read sensitive data with no server-side authz
check; admin/debug/actuator endpoints reachable without auth; object ids taken from the
request (`/orders/:id`) and used without verifying the caller owns the object (IDOR);
authz decided in the client/UI only; mass-assignment binding request bodies straight to
models; role checks that trust a request-supplied role field.

**Impact:** privilege escalation, one user reading/altering another's data, full admin
takeover.

**Fix:** enforce authorization server-side on every protected action; deny by default;
check *ownership*, not just authentication; bind an allow-list of fields, never the whole
body; put admin surfaces behind auth + network restriction; remove/secure debug endpoints
in production.

## 3. Authentication, sessions & credentials

**Look for:** password stored plaintext or hashed with MD5/SHA1/unsalted; no lockout/rate
limit on login; session tokens from `Math.random()`/timestamps; sessions that never
expire or don't rotate on privilege change; JWT with `alg: none` or a hardcoded/weak
secret; "remember me" tokens that don't expire; missing re-auth on sensitive actions.

**Impact:** account takeover, credential stuffing, session hijacking.

**Fix:** hash with `bcrypt`/`argon2id`/`scrypt` + per-user salt; rate-limit and lock out
brute force; generate tokens from a CSPRNG; expire and rotate sessions; verify JWT alg and
signature with a strong secret/keypair.

## 4. Secrets in code & config

**Look for:** API keys, passwords, private keys (`-----BEGIN ... PRIVATE KEY-----`),
cloud creds (`AKIA...`), DB connection strings with passwords, tokens hardcoded in source,
config, Dockerfiles, CI YAML, or committed `.env`.

**Impact:** anyone with repo/read access (or a leaked archive) owns the credential.

**Fix:** move to environment variables or a secret manager; **rotate the exposed value —
it is already compromised**; purge from git history (`git filter-repo`); add to
`.gitignore`; add a pre-commit secret scanner.

## 5. Database exposure

**Look for:** connection strings with embedded passwords; a single DB account with full
privileges used by the app; database bound to `0.0.0.0` with no firewall; backups/dumps in
web-served or world-readable paths; queries with no `LIMIT` on user-facing lists; missing
row-level authorization; ORM `raw()`/`extra()` with interpolation.

**Impact:** mass data exfiltration, tampering, DoS via huge result sets.

**Fix:** least-privilege DB accounts per service; secrets out of the connection string;
network-isolate the DB; store backups encrypted and access-controlled; parameterize; add
`LIMIT`/pagination; enforce tenant/row scoping in every query.

## 6. Sensitive data & PII exposure

**Look for:** PII/secrets written to logs, error messages, or API responses; stack traces
returned to clients; `debug=True` in production; PII in URLs (logged everywhere); missing
encryption at rest for sensitive fields; overly broad API serializers returning internal
fields.

**Impact:** privacy breach, regulatory exposure, secret leakage via logs.

**Fix:** redact secrets/PII from logs; generic error pages to clients, details to internal
logs only; disable debug in prod; encrypt sensitive columns; serialize an explicit
allow-list of fields.

## 7. XSS (reflected / stored / DOM)

**Look for:** user input rendered into HTML without encoding; `innerHTML`,
`dangerouslySetInnerHTML`, `v-html`, `document.write` with input; template auto-escaping
disabled (`| safe`, `{{{ }}}`, `mark_safe`); reflected params echoed into pages.

**Impact:** session theft, action-on-behalf-of-user, credential phishing in-page.

**Fix:** context-aware output encoding; rely on framework auto-escaping; add a strict
`Content-Security-Policy`; sanitize rich HTML with a vetted library; never build HTML from
raw input.

## 8. SSRF, CSRF, CORS & security headers

**Look for:** server fetches a URL/host taken from user input (SSRF); state-changing routes
without CSRF tokens or `SameSite` cookies; `Access-Control-Allow-Origin: *` combined with
credentials, or reflecting the Origin header; missing `Content-Security-Policy`,
`Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options`.

**Impact:** internal-service/metadata access (SSRF), forged state changes (CSRF),
cross-origin data theft (CORS), clickjacking/MIME sniffing (headers).

**Fix:** SSRF — allow-list destinations, block RFC1918/link-local/metadata IPs, disallow
user-controlled host; CSRF — anti-CSRF tokens + `SameSite=Lax/Strict`; CORS — reflect only
vetted origins, never `*` with credentials; set the security headers globally.

## 9. Insecure deserialization, path traversal & file upload

**Look for:** `pickle.loads`, `yaml.load` (non-safe), Java/PHP native deserialization on
untrusted bytes; file paths built from user input (`open(base + name)`, `../`); uploads
without type/size/extension validation or stored in a web-executable dir.

**Impact:** remote code execution, arbitrary file read/write, malware hosting.

**Fix:** avoid native deserialization of untrusted data (use JSON); `yaml.safe_load`;
canonicalize and confine paths under a base dir (reject `..`); validate upload
type/size/extension, store outside the web root, randomize names, serve non-executable.

## 10. Denial of service / resource exhaustion (DDoS resilience)

**Look for:** no rate limiting on login, search, export, or other expensive endpoints;
unbounded request-body or upload size; list queries without `LIMIT`; regex with nested
quantifiers on user input (ReDoS); no timeout on outbound HTTP/DB calls; recursion or
loops whose depth/count comes from user input; zip/xml expansion (zip bomb, billion
laughs).

**Impact:** a single client (or a small botnet) exhausts CPU/memory/connections and takes
the service down — application-layer DoS.

**Fix:** rate-limit and throttle at the gateway/app (per-IP and per-account); cap body and
upload size; paginate and `LIMIT` queries; set timeouts on every outbound call; replace
catastrophic regex; bound recursion/iteration by a constant; disable external entity
expansion. Keep each limit a tunable constant, not a magic number buried in a branch.

## 11. Weak cryptography

**Look for:** MD5/SHA1 for security purposes; DES/RC4/ECB mode; static or reused IV/nonce;
`Math.random()`/`rand()` for tokens/keys; hardcoded keys; TLS verification disabled
(`verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify`).

**Impact:** breakable encryption, forgeable tokens, MITM.

**Fix:** AES-GCM (or libsodium) with random per-message nonce; SHA-256+ for hashing;
password KDFs (§3) for passwords; CSPRNG for tokens; keys in a secret manager; never
disable TLS verification.

## 12. Vulnerable & malicious dependencies

**Look for:** pinned versions with known CVEs; unmaintained packages; typosquatted or
suspicious new deps; lockfile drift.

**Impact:** inherited RCE/data-exposure through third-party code.

**Fix:** run the ecosystem auditor (`npm audit`, `pip-audit`, `govulncheck`, `bundle
audit`, `osv-scanner`); bump to patched versions; remove/replace unmaintained or suspect
packages; commit lockfiles.

---

## Data-flow rule (applies to every class)

A pattern match is only a vulnerability if untrusted input can actually **reach** the
dangerous sink. Trace source → transformations → sink. If validation/encoding/parameter-
ization already sits on the path, it may be safe. If the source is fully trusted
(hardcoded constant, server config), it's not the same finding. Confirm reachability
before you call it a bug — and before you spend a fix on it.
