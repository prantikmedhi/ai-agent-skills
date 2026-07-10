---
description: Route a request through the Fable 5 effort router (thinking depth, effort tier, artifact decision)
allowed-tools: Bash(python3:*)
---
Run the Fable 5 effort router on the request below using the Bash tool:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/fable5-operating-profile/scripts/effort_router.py" --text "<request>" --json
```

Report the routing verdict in one line (think depth, reasoning effort, artifact
decision, interleave/verify flags), then answer the request itself following that
verdict.

Request: $ARGUMENTS
