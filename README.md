# gz-claude-code-plugins

A personal Claude Code plugin marketplace containing Gavin's plugins and curated third-party plugins.

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [claude-transcript-exporter](plugins/claude-transcript-exporter/) | Exports session transcripts on session end |

## Installation

```bash
# Add this marketplace (one-time setup)
/plugin marketplace add https://github.com/CaptainCodeAU/gz-claude-code-plugins.git

# Install a specific plugin
/plugin install claude-transcript-exporter@gz-claude-code-plugins
```

## Structure

- `plugins/` — First-party plugins by Gavin
- `external_plugins/` — Curated third-party plugins (vendored)

## Issues

Report issues at [github.com/CaptainCodeAU/gz-claude-code-plugins/issues](https://github.com/CaptainCodeAU/gz-claude-code-plugins/issues).

## License

First-party plugins are MIT licensed. External plugins retain their original licenses — see individual plugin directories for details.
