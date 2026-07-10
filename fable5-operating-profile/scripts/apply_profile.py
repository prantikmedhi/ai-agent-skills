#!/usr/bin/env python3
"""
apply_profile.py — run any model under the Fable 5 operating profile.

Prepends fable5_system_prompt.md as the system prompt and sends your prompt to the
chosen provider. Works with Anthropic (Opus 4.8, Sonnet, Fable) and OpenAI
(GPT / Codex) models. Stdlib only — no SDK install required.

Optionally runs the local preflight (cyber_guard) + router (effort_router) first,
so the same four-dimension behavior applies even to models that never saw the prompt.

Usage:
    export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY=...
    python3 apply_profile.py --provider anthropic --model claude-opus-4-8 --prompt "Review this plan"
    python3 apply_profile.py --provider openai --model gpt-5-codex --prompt "Refactor X" --preflight
    python3 apply_profile.py --provider anthropic --model claude-sonnet-4-6 --prompt "..." --dry-run

--dry-run builds and prints the exact request without any API key or network call.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent.parent / "fable5_system_prompt.md"

ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/chat/completions",
}


def load_profile() -> str:
    return PROFILE_PATH.read_text()


def build_request(provider, model, prompt, system, max_tokens):
    if provider == "anthropic":
        url = ENDPOINTS["anthropic"]
        headers = {
            "content-type": "application/json",
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
    elif provider == "openai":
        url = ENDPOINTS["openai"]
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
    else:
        raise ValueError(f"unknown provider: {provider}")
    return url, headers, body


def extract_text(provider, data):
    if provider == "anthropic":
        return "".join(b.get("text", "") for b in data.get("content", []))
    return data["choices"][0]["message"]["content"]


def send(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"network error: {e.reason}")


def preflight(prompt):
    """Optional local guard + route using the sibling scripts."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cyber_guard  # noqa: E402
    import effort_router  # noqa: E402
    guard = cyber_guard.scan(prompt)
    route = effort_router.route(prompt)
    print(f"[preflight] cyber verdict: {guard['verdict']} — {guard['note']}", file=sys.stderr)
    print(f"[preflight] route: think={route['think']} effort={route['effort']} "
          f"artifact={route['artifact']['kind']}", file=sys.stderr)
    if guard["verdict"] == "block":
        sys.exit("[preflight] blocked by cyber_guard — refusing to send.")
    return guard, route


def main():
    ap = argparse.ArgumentParser(description="Run any model under the Fable 5 profile")
    ap.add_argument("--provider", choices=list(ENDPOINTS), required=True)
    ap.add_argument("--model", required=True,
                    help="e.g. claude-opus-4-8, claude-sonnet-4-6, gpt-5-codex")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--preflight", action="store_true",
                    help="run cyber_guard + effort_router locally first")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the request without calling the API")
    args = ap.parse_args()

    system = load_profile()
    if args.preflight:
        preflight(args.prompt)

    url, headers, body = build_request(args.provider, args.model, args.prompt,
                                       system, args.max_tokens)

    if args.dry_run:
        redacted = {k: ("<redacted>" if k in ("x-api-key", "authorization") else v)
                    for k, v in headers.items()}
        print(json.dumps({"url": url, "headers": redacted,
                          "body_preview": {**body, "system": system[:80] + "…"}},
                         indent=2))
        return

    key_env = "ANTHROPIC_API_KEY" if args.provider == "anthropic" else "OPENAI_API_KEY"
    if not os.environ.get(key_env):
        sys.exit(f"missing {key_env}. Set it or use --dry-run.")

    data = send(url, headers, body)
    print(extract_text(args.provider, data))


if __name__ == "__main__":
    main()
