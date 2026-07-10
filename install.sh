#!/usr/bin/env bash
# Install skills from this repo into Claude Code, and build zips for Claude Desktop / claude.ai.
#
#   ./install.sh              install all skills into ~/.claude/skills (Claude Code, global)
#   ./install.sh --zip        also build dist/*.zip for upload to Claude Desktop / claude.ai
#   ./install.sh --uninstall  remove installed skills from ~/.claude/skills
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

# skill name -> source directory (each contains a SKILL.md)
SKILL_PATHS=(
  "fable5-operating-profile:$REPO_DIR/fable5-operating-profile/skills/fable5-operating-profile"
  "auto-skill-finder:$REPO_DIR/auto-skill-finder"
)

if [[ "${1:-}" == "--uninstall" ]]; then
  for entry in "${SKILL_PATHS[@]}"; do
    name="${entry%%:*}"
    rm -rf "${SKILLS_DIR:?}/$name"
    echo "removed $SKILLS_DIR/$name"
  done
  exit 0
fi

mkdir -p "$SKILLS_DIR"
for entry in "${SKILL_PATHS[@]}"; do
  name="${entry%%:*}" src="${entry#*:}"
  [[ -f "$src/SKILL.md" ]] || { echo "error: no SKILL.md in $src" >&2; exit 1; }
  rm -rf "${SKILLS_DIR:?}/$name"
  # copy without nested .git / node_modules
  rsync -a --exclude '.git' --exclude 'node_modules' --exclude 'caveman/.git' "$src/" "$SKILLS_DIR/$name/"
  echo "installed $name -> $SKILLS_DIR/$name"
done

if [[ "${1:-}" == "--zip" ]]; then
  mkdir -p "$REPO_DIR/dist"
  for entry in "${SKILL_PATHS[@]}"; do
    name="${entry%%:*}" src="${entry#*:}"
    ( cd "$(dirname "$src")" && zip -qr "$REPO_DIR/dist/$name.zip" "$(basename "$src")" -x '*/.git/*' '*/node_modules/*' )
    echo "built dist/$name.zip  (upload in Claude Desktop / claude.ai: Settings -> Capabilities -> Skills)"
  done
fi

echo "done. Restart Claude Code to pick up new skills."
