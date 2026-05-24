# Spec: gz-claude-code-plugins Marketplace

A personal Claude Code plugin marketplace containing Gavin's plugins and curated third-party plugins.

**Author:** Gavin (personal marketplace, not part of PAI)
**Date:** 2026-04-24
**Status:** Ready for implementation

---

## Marketplace Overview

**Repo:** `CaptainCodeAU/gz-claude-code-plugins`

A single git repository functioning as a Claude Code plugin marketplace. Contains multiple
independently installable plugins — both first-party (Gavin's own) and curated third-party.

### Repository Structure

```
gz-claude-code-plugins/
├── plugins/                              # First-party plugins (by Gavin)
│   └── claude-transcript-exporter/       # First plugin (see below)
├── external_plugins/                     # Curated third-party plugins (vendored)
│   └── .gitkeep
├── README.md                             # Marketplace overview + install instructions
└── LICENSE
```

### How It Works

Users add this repo as a marketplace once, then selectively install any plugin from it:

```bash
# Add marketplace (one-time setup)
/plugin marketplace add https://github.com/CaptainCodeAU/gz-claude-code-plugins.git

# Browse and install specific plugins
/plugin install claude-transcript-exporter@gz-claude-code-plugins
```

### Adding New Plugins

**First-party:** Create a new directory under `plugins/` with the standard plugin structure
(`.claude-plugin/plugin.json`, hooks/, skills/, etc.). Each plugin is independent.

**Third-party (vendored):** Copy the external plugin into `external_plugins/`, preserving the
original `plugin.json` author field and LICENSE. Pin to a specific version/commit. You're
responsible for pulling updates manually.

### Marketplace README.md

The README should include:
- What this marketplace is and who maintains it
- Table of available plugins with one-line descriptions
- Installation instructions (add marketplace + install plugin)
- How to report issues
- Attribution notes for external plugins

---

# Plugin: claude-transcript-exporter

The first plugin in this marketplace. Exports session transcripts on session end.

## What It Does

When a Claude Code session ends (for any reason), this plugin runs `claude-code-transcripts`
to convert the session's JSONL transcript into a structured format and saves it to a
configurable output directory.

Default output: `~/CODE/my-claude-code-transcripts`

## Why a Plugin

This was originally a project-level hook in the dotfiles repo (`.claude/hooks/export_transcript.sh`).
Moving it to a plugin means:

- Works across ALL projects globally, not just dotfiles
- Completely independent from PAI hooks and infrastructure
- Easy to install, uninstall, version, and share
- Lives in a personal marketplace repo alongside other plugins

## Plugin Structure

Lives at `plugins/claude-transcript-exporter/` inside the marketplace repo. Follows the
official Anthropic plugin conventions from
[claude-plugins-official](https://github.com/anthropics/claude-plugins-official).

```
plugins/claude-transcript-exporter/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest (required)
├── hooks/
│   ├── hooks.json               # SessionEnd hook registration
│   └── export-transcript.py     # Export logic
└── README.md
```

`LICENSE` lives at the marketplace root and covers all first-party plugins.

Key conventions from the official repo:

- `plugin.json` is minimal: name, description, author (version is optional -- if omitted,
  the git commit SHA is used, and every commit counts as a new version)
- Hook scripts use `${CLAUDE_PLUGIN_ROOT}` to reference files within the plugin directory.
  This variable is provided by Claude Code and resolves to wherever the plugin is installed
- Default timeout is 60s for command hooks. We use 15s since the CLI should finish quickly
- `README.md` per plugin is recommended; `LICENSE` is at marketplace root
- `commands/` holds flat .md slash commands; `skills/` holds subdirectories with SKILL.md
  for auto-activated skills. Both are valid — we don't need either for v1

### plugin.json

```json
{
  "name": "claude-transcript-exporter",
  "description": "Exports Claude Code session transcripts on session end",
  "author": {
    "name": "Gavin"
  }
}
```

No `version` field -- using git SHA versioning so every commit to the marketplace repo
is automatically a new version without manual bumping.

### hooks/hooks.json

Plugin `hooks.json` uses a wrapper format with an optional `description` field — different
from user `settings.json` which uses the event types directly at the top level.

```json
{
  "description": "Export session transcripts on session end",
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/export-transcript.py",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

No matcher is set, so the hook fires on ALL SessionEnd subtypes:
`clear`, `resume`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`.

This is intentional. If a session produced a transcript, it should be exported regardless
of how the session ended. Double-firing is not possible because SessionEnd fires once per
session with a single reason value, and Claude Code deduplicates identical hooks by
command string.

**Why Python, not TypeScript?** The official hookify plugin from Anthropic uses `python3`
for hook scripts (no external dependencies, stdlib only). Python is available everywhere,
doesn't require Bun, and keeps the plugin self-contained with zero runtime dependencies
beyond Python 3.7+. This also avoids coupling to Bun/Node which are PAI dependencies.

### hooks/export-transcript.py

The script:

1. Reads stdin JSON from Claude Code (see SessionEnd Payload Reference below)
2. Validates the transcript file exists at `transcript_path`
3. Resolves the project name via fallback chain (see Project Resolution below)
4. Reads output directory from `TRANSCRIPT_EXPORT_DIR` env var
   (defaults to `~/CODE/my-claude-code-transcripts`)
5. Creates `<output-dir>/<project-name>/` if needed
6. Skips if session already exported (duplicate detection)
7. Runs `claude-code-transcripts json <path> -o <project-dir> -a --json`
8. Reports outcome via macOS notification, voice server, and JSONL log
9. Opens the exported session folder in Finder on success
10. Exits 0 always (never blocks session end)
11. Skips entirely if `SKIP_SESSION_END_HOOK=1` is set

All failures are reported (never silent). The hook still exits 0 to avoid blocking
session end, but errors are visible via notification, voice, and log.

### Project Resolution

The plugin determines which project folder to export into using a fallback chain:

1. **Transcript path parent directory** (primary) — the `~/.claude/projects/`
   encoded folder name. This is the exact same input the `all` command passes to
   `get_project_display_name()`, guaranteeing consistent archive folder names
   between plugin exports and batch exports.
2. **SessionEnd payload `cwd`** — from the hook's stdin JSON payload, encoded to
   match Claude Code's path conventions (both `/` and `_` replaced with `-`).
3. **JSONL `cwd` field** — reads the first entry with a non-empty `cwd` from the
   transcript JSONL, with the same encoding applied.
4. **`_unresolved/`** — final fallback to avoid root-level orphan folders.

### `get_project_display_name()`

Reimplemented from `claude-code-transcripts` CLI (~25 lines, pure function).
Converts an encoded folder name like `-Users-fonzarelli-CODE-CaptainCodeAU-Tax-Bhencho`
into `CaptainCodeAU-Tax-Bhencho`:

1. Strip OS prefixes: `-Users-`, `-home-`, `-mnt-c-Users-`, `-mnt-c-users-`
2. Split on `-`
3. Skip first part if it looks like a username (when common dirs appear later)
4. Skip common dirs: `projects`, `code`, `repos`, `src`, `dev`, `work`, `documents`
5. Join remaining parts with `-`
6. Fallback: last non-empty part, or original name

### Output Structure

```
~/CODE/my-claude-code-transcripts/
  CaptainCodeAU-Tax-Bhencho/
    f1a2a7f0-5057-.../
      index.html
      page-001.html
      f1a2a7f0-5057-...jsonl
  fonzarelli-claude/
    ...
  _unresolved/              # Sessions where project could not be determined
    ...
```

### Error Reporting

Every export attempt is reported three ways:

1. **Desktop notification** — macOS (`osascript`) or Linux (`notify-send`) with title "Claude Transcripts"
   - Success: "Session exported -> ProjectName"
   - Failure: "Export failed: reason"
2. **Voice server** — POST to `localhost:8888/notify`
   - Success: speaks project name
   - Failure: speaks error reason
3. **JSONL log file** — `~/.claude/logs/transcript-export.log`
   - One JSON line per attempt: `ts`, `session_id`, `project`, `status`, `error`, `duration_ms`

## Configuration

The output directory defaults to `~/CODE/my-claude-code-transcripts` on macOS and
`~/my-claude-code-transcripts` on Linux.

Users can override it by setting the `TRANSCRIPT_EXPORT_DIR` environment variable
(e.g., in their shell profile or in Claude Code's `settings.json` env section).

## Dependencies

- Python 3.7+ (stdlib only, no pip packages)
- `claude-code-transcripts` CLI via `uv tool install` (optional -- auto-fetched via `uv tool run` if not installed)

## SessionEnd Payload Reference

Claude Code sends this JSON on stdin for SessionEnd hooks. Common fields (`session_id`,
`transcript_path`, `cwd`, `permission_mode`, `hook_event_name`) are sent to ALL hook types.

```typescript
{
  session_id: string;
  transcript_path: string; // absolute path to the session's .jsonl transcript
  cwd: string;
  permission_mode: string; // current permission mode
  hook_event_name: "SessionEnd";
  reason: string; // why the session ended (see table below)
}
```

Valid `reason` values (use `"matcher": "logout|clear"` in hooks.json to filter on specific reasons):

| Reason                        | Meaning                                |
| ----------------------------- | -------------------------------------- |
| `clear`                       | User ran `/clear`                      |
| `resume`                      | User ran `/resume` to switch sessions  |
| `logout`                      | User logged out                        |
| `prompt_input_exit`           | Session exited via prompt input ending |
| `bypass_permissions_disabled` | Bypass permissions mode was disabled   |
| `other`                       | Any other termination reason           |

**Note:** The PAI THEHOOKSYSTEM.md (lines 1058-1064) incorrectly documents this payload as
`{ conversation_id, timestamp }`. The payload above is the actual structure, verified against
the official Claude Code documentation at code.claude.com/docs/en/hooks (April 2026).

## Execution Order

Plugin hooks run alongside global `settings.json` hooks. Since this hook has no dependencies
on any other hook's output (it only reads the transcript file, which no hook modifies), ordering
does not matter.

## Migration Steps

After the plugin is installed globally:

1. Remove the `export_transcript.sh` hook and its SessionEnd registration from the
   dotfiles project (`fifty-shades-of-dotfiles/.claude/hooks/export_transcript.sh`
   and its corresponding entry in the project's `.claude/settings.json`) to prevent
   double execution. Note: this is a project-level hook, not in the global
   `~/.claude/settings.json` (which only has PAI hooks)
2. Check for any other project-level copies of this hook (it was templated into
   multiple project directories)

## Development and Testing

```bash
# Test a single plugin locally without installing (from marketplace root)
claude --plugin-dir ./plugins/claude-transcript-exporter

# Verify hook fires on session end
# (exit the session and check ~/CODE/my-claude-code-transcripts for output)

# Add the marketplace (one-time setup)
/plugin marketplace add https://github.com/CaptainCodeAU/gz-claude-code-plugins.git

# Install this plugin from the marketplace
/plugin install claude-transcript-exporter@gz-claude-code-plugins
```

## Future Ideas

- Add a skill (`/transcript-exporter:status`) to show export stats or recent exports
- Support multiple output formats (HTML, markdown) via config
- Add a monitor that watches the output directory and reports stats at session start
- Use `${CLAUDE_PLUGIN_DATA}` for persistent storage — track export history,
  last-exported timestamps, or export stats across sessions
