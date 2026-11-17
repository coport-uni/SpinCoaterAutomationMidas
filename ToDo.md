# ToDo

## Adopt CommonClaude harness and hooks

### Background
User request (2026-11-17): add https://github.com/coport-uni/CommonClaude
as a submodule under `external/`, then apply its Claude Code harness and
hooks to this repository.
Issue: https://github.com/coport-uni/SpinCoaterAutomationMidas/issues/1

### Tasks
- [x] Add `external/CommonClaude` as a git submodule
- [x] Copy `.claude/settings.json` (env, Pre/PostToolUse hooks, Stop hook)
- [x] Copy the five hook scripts into `.claude/hooks/`
- [x] Create root `CLAUDE.md` that imports
      `@external/CommonClaude/CLAUDE.md`
- [x] Smoke-test each hook with sample JSON input
- [x] Register GitHub issue via `gh issue create` (#1)
- [ ] Commit on a working branch and open a PR (awaiting user approval)

### Notes
- The generic credential patterns in `pre-bash-secret-scan.sh` are
  case-sensitive, so an all-uppercase key name is not detected while a
  lowercase one is. Inherited from upstream CommonClaude.
