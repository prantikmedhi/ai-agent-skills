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

## Use — just type `/`

No code needed. After install, everything is slash-invocable in Claude Code:

| Command | Does |
|---------|------|
| `/fable5` | Apply the full Fable 5 operating profile for the rest of the session. |
| `/fable5-route <request>` | Route a request: thinking depth, effort tier, artifact decision. |
| `/fable5-guard <text or file>` | Scan input for injection/exfiltration/secrets → allow / confirm / block. |
| `/auto-skill <prompt>` | Route a prompt to the best installed skill manually. |
| `/fable5-operating-profile`, `/auto-skill-finder` | Invoke the skills directly by name. |

auto-skill-finder also runs automatically on every prompt via its hooks — no command
needed at all.

In **Claude Desktop / claude.ai**, upload the zips (`./install.sh --zip`) and the
skills trigger automatically when relevant, or on request by name ("use the fable5
operating profile"). Custom slash commands are a Claude Code feature.

## Repo layout

```
.claude-plugin/marketplace.json      # marketplace manifest (both plugins)
install.sh                           # Claude Code install + Claude Desktop zip builder
fable5-operating-profile/
├── .claude-plugin/plugin.json
├── commands/                        # /fable5, /fable5-route, /fable5-guard
├── README.md
└── skills/fable5-operating-profile/ # SKILL.md + prompt + scripts + references
auto-skill-finder/
├── .claude-plugin/plugin.json       # hooks: SessionStart + UserPromptSubmit routing
├── commands/                        # /auto-skill
├── README.md
├── SKILL.md
└── skills/                          # ponytail-code, caveman-chat, caveman-code
```

## License

MIT
