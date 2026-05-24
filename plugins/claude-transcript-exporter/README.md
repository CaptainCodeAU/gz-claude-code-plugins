# claude-transcript-exporter

Exports Claude Code session transcripts on session end into project-organized folders.

When a Claude Code session ends (for any reason), this plugin:
1. Determines the project from the session's JSONL `cwd` field
2. Exports the transcript into `<output_dir>/<project_name>/<session_uuid>/`
3. Reports success/failure via macOS notification, voice, and log file

## Output structure

```
~/CODE/my-claude-code-transcripts/
  CaptainCodeAU-Tax-Bhencho/
    f1a2a7f0-5057-.../
      index.html
      page-001.html
      f1a2a7f0-5057-...jsonl
  fonzarelli-claude/
    ...
```

## Project resolution

The plugin determines the project folder name using a fallback chain:
1. **Transcript path parent directory** — the `~/.claude/projects/` encoded folder name, guaranteeing consistent naming with the `all` command
2. **SessionEnd payload `cwd`** — from the hook's stdin payload, encoded to match Claude Code's path conventions
3. **JSONL `cwd` field** — reads the first `cwd` entry from the transcript
4. **`_unresolved/`** — final fallback to avoid root-level orphan folders

## Error reporting

Every export attempt is reported three ways:
- **macOS notification** — "Session exported → ProjectName" or "Export failed: reason"
- **Voice** — speaks via voice server at `localhost:8888`
- **Log file** — JSONL at `~/.claude/logs/transcript-export.log`

## Installation

```bash
# Add the marketplace (one-time)
/plugin marketplace add https://github.com/CaptainCodeAU/gz-claude-code-plugins.git

# Install this plugin
/plugin install claude-transcript-exporter@gz-claude-code-plugins
```

Or test locally:

```bash
claude --plugin-dir ./plugins/claude-transcript-exporter
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIPT_EXPORT_DIR` | `~/CODE/my-claude-code-transcripts` | Output directory for exported transcripts |
| `SKIP_SESSION_END_HOOK` | unset | Set to `1` to disable the export hook |

Set `TRANSCRIPT_EXPORT_DIR` in your shell profile or in Claude Code's `settings.json` env section.

## Dependencies

- Python 3.7+ via [uv](https://docs.astral.sh/uv/) (stdlib only)
- [`claude-code-transcripts`](https://github.com/CaptainCodeAU/claude-code-transcripts) CLI on PATH
