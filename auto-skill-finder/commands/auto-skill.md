---
description: Route a prompt through auto-skill-finder (detect intent, pick best installed skill, execute)
---
Follow the auto-skill-finder routine from
`${CLAUDE_PLUGIN_ROOT}/SKILL.md` on the prompt below:

1. Detect intent (code → ponytail-code mode, chat → caveman-chat mode).
2. Scan installed skills (`~/.claude/skills/*/SKILL.md`, plugin skills).
3. Score and pick the best match; load it if score ≥ 5.
4. Execute the prompt in the active mode.

Prompt: $ARGUMENTS
