# ai-agent-skills

Skills and plugins for Claude Code, Claude Desktop, and any agent that reads `SKILL.md`.
This repo is also a **Claude Code plugin marketplace** — one command adds everything.

| Skill / Plugin | What it does | Docs |
|----------------|--------------|------|
| [fable5-operating-profile](fable5-operating-profile/) | Run any model with Fable 5's operating profile: interleaved thinking, effort routing, autonomous agency, outcome-first communication, prompt-injection defense, tool discipline. | [README](fable5-operating-profile/README.md) |
| [auto-skill-finder](auto-skill-finder/) | Universal skill router with dual-mode discipline — ponytail for code, caveman for chat. Auto-routes every prompt to the best installed skill. | [README](auto-skill-finder/README.md) |

## Install

### Claude Code — plugin marketplace (recommended)

```
/plugin marketplace add prantikmedhi/ai-agent-skills
/plugin install fable5-operating-profile@ai-agent-skills
/plugin install auto-skill-finder@ai-agent-skills
```

### Claude Code — one-command script

```bash
git clone https://github.com/prantikmedhi/ai-agent-skills.git
cd ai-agent-skills && ./install.sh
```

Copies both skills into `~/.claude/skills/` (set `CLAUDE_SKILLS_DIR` to override).
Restart Claude Code afterwards. Uninstall with `./install.sh --uninstall`.

### Claude Desktop / claude.ai

```bash
./install.sh --zip
```

Builds `dist/<skill>.zip`, then upload in **Settings → Capabilities → Skills**.

### Manual

Copy any skill folder containing a `SKILL.md` into `~/.claude/skills/` (global) or
`.claude/skills/` inside a project.

## Repo layout

```
.claude-plugin/marketplace.json      # marketplace manifest (both plugins)
install.sh                           # Claude Code install + Claude Desktop zip builder
fable5-operating-profile/
├── .claude-plugin/plugin.json
├── README.md
└── skills/fable5-operating-profile/ # SKILL.md + prompt + scripts + references
auto-skill-finder/
├── .claude-plugin/plugin.json       # hooks: SessionStart + UserPromptSubmit routing
├── README.md
├── SKILL.md
└── skills/                          # ponytail-code, caveman-chat, caveman-code
```

## License

MIT
