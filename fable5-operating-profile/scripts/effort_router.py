#!/usr/bin/env python3
"""
effort_router.py — Fable 5 "auto thinking" + "stop at the first rung" router.

Given a request, decide:
  - think:   none | brief | deep     (how much reasoning the model should spend)
  - effort:  minimal | moderate | high
  - artifact: whether an artifact/visual/file is warranted, and which kind

Heuristic only — a cheap classifier, not a model. It exists so an agent doesn't
under-think hard problems or over-produce on easy ones. Tune the keyword sets for
your domain; that's the calibration knob a static model can't see.

Usage:
    python3 effort_router.py --text "what's the capital of France?"
    echo "design a distributed rate limiter" | python3 effort_router.py --stdin
    python3 effort_router.py --text "..." --json
    python3 effort_router.py --selftest
"""
import argparse
import json
import re
import sys

# ponytail: flat keyword heuristics, not an ML model. Upgrade to embeddings only if
# routing accuracy measurably matters.

HARD = [
    "design", "architect", "architecture", "prove", "derive", "optimize",
    "algorithm", "distributed", "concurren", "fault-toleran", "trade-off",
    "tradeoff", "migrate", "refactor the", "end-to-end", "threat model",
    "security review", "why does", "root cause", "debug", "reconcile",
    "strategy", "plan for", "multi-step", "step by step",
]
TRIVIAL = [
    "capital of", "what time", "define ", "definition of", "spell", "translate",
    "convert ", "how do you say", "what is the", "who is the", "say hi", "hello",
    "thanks", "thank you", "what's the date",
]
ARTIFACT_INTENT = [
    "write up", "as a doc", "document", "report", "essay", "slide", "deck",
    "presentation", "spreadsheet", "table of", "script", "component", "app",
    "build me", "create a file", "generate a", "make a", "landing page",
]
VISUAL_INTENT = [
    "show me", "diagram", "chart", "graph", "visualize", "visualise", "draw",
    "flowchart", "plot", "map of", "timeline",
]
# irreversible / high-stakes -> force deeper thinking regardless of length
STAKES = [
    "delete", "drop table", "production", "prod ", "money", "payment", "wire",
    "irreversible", "migrate the database", "rm -rf", "overwrite", "deploy",
    "legal", "medical", "financial advice",
]


def _hit(text, needles):
    return sorted({n.strip() for n in needles if n in text})


def route(request: str) -> dict:
    t = request.lower()
    words = len(re.findall(r"\w+", t))

    hard = _hit(t, HARD)
    trivial = _hit(t, TRIVIAL)
    stakes = _hit(t, STAKES)
    artifact_words = _hit(t, ARTIFACT_INTENT)
    visual_words = _hit(t, VISUAL_INTENT)

    # ---- thinking depth (auto) ----
    if stakes or hard or words > 60:
        think = "deep"
    elif trivial and words <= 12 and not artifact_words:
        think = "none"
    else:
        think = "brief"

    # ---- effort tier ----
    if think == "deep":
        effort = "high"
    elif think == "none":
        effort = "minimal"
    else:
        effort = "moderate"

    # ---- artifact decision (does it earn its place?) ----
    if artifact_words:
        kind = "document"
        if any(w in t for w in ("slide", "deck", "presentation")):
            kind = "presentation"
        elif any(w in t for w in ("spreadsheet", "table of", "budget", "xlsx")):
            kind = "spreadsheet"
        elif any(w in t for w in ("component", "app", "landing page", "jsx", "html")):
            kind = "code/frontend"
        artifact = {"warranted": True, "kind": kind}
    elif visual_words:
        artifact = {"warranted": True, "kind": "visual"}
    else:
        # default: prose. An artifact must be explicitly earned.
        artifact = {"warranted": False, "kind": "prose"}

    # verification is mandatory once logic/stakes are involved
    verify = think == "deep" or bool(stakes)

    return {
        "think": think,
        "effort": effort,
        "artifact": artifact,
        "verify_before_commit": verify,
        "signals": {
            "words": words,
            "hard": hard,
            "trivial": trivial,
            "stakes": stakes,
            "artifact_intent": artifact_words,
            "visual_intent": visual_words,
        },
    }


def _fmt(r: dict) -> str:
    a = r["artifact"]
    art = f"{a['kind']}" if a["warranted"] else "no (prose)"
    v = "  | verify before commit" if r["verify_before_commit"] else ""
    return f"think: {r['think']} | effort: {r['effort']} | artifact: {art}{v}"


def _selftest():
    cases = [
        ("what's the capital of France?", "none", "minimal", False),
        ("hello", "none", "minimal", False),
        ("design a fault-tolerant job queue and write it up as a doc", "deep", "high", True),
        ("refactor the auth module and deploy to production", "deep", "high", True),
        ("summarize this article in a sentence or two", "brief", "moderate", False),
        ("draw me a flowchart of the login flow", "brief", "moderate", False),
    ]
    for text, ethink, eeffort, everify in cases:
        r = route(text)
        assert r["think"] == ethink, f"think {r['think']}!={ethink} for {text!r}"
        assert r["effort"] == eeffort, f"effort {r['effort']}!={eeffort} for {text!r}"
        assert r["verify_before_commit"] == everify, f"verify mismatch for {text!r}"
    # artifact decisions
    assert route("write up a report on X")["artifact"]["warranted"] is True
    assert route("draw me a chart")["artifact"]["kind"] == "visual"
    assert route("what is 2+2")["artifact"]["warranted"] is False
    print("effort_router selftest: OK")


def main():
    ap = argparse.ArgumentParser(description="Fable 5 thinking/effort router")
    ap.add_argument("--text")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    text = args.text or (sys.stdin.read() if args.stdin else None)
    if not text or not text.strip():
        ap.error("provide --text, --stdin, or --selftest")
    r = route(text)
    print(json.dumps(r, indent=2) if args.json else _fmt(r))


if __name__ == "__main__":
    main()
