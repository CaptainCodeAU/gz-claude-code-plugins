# claude-transcript-exporter

Exports Claude Code session transcripts on session end.

When a Claude Code session ends (for any reason), this plugin runs `claude-code-transcripts` to convert the session's JSONL transcript into a structured format and saves it to a configurable output directory.

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
- [`claude-code-transcripts`](https://github.com/anthropics/claude-code-transcripts) CLI on PATH
