#!/usr/bin/env python3
"""SessionEnd wrapper: set personal env, then delegate the whole capture
pipeline to the claude-code-transcripts CLI (the single source of truth).

No business logic lives here anymore — naming, cwd-first resolution, the
idempotency skip, JSONL filing, notifications, and the detached HTML render are
all owned by `claude-code-transcripts hook`.
"""
import os
import sys
import subprocess

IS_MACOS = sys.platform == "darwin"

env = dict(os.environ)
env.setdefault(
    "TRANSCRIPT_EXPORT_DIR",
    os.path.expanduser(
        "~/CODE/my-claude-code-transcripts" if IS_MACOS else "~/my-claude-code-transcripts"
    ),
)
# Voice notifications are opt-in on the flagship side; preserve the current setup.
env.setdefault("TRANSCRIPT_VOICE_URL", "http://localhost:8888/notify")
env.setdefault("TRANSCRIPT_VOICE_ID", "fTtv3eikoepIosk8dTZ5")

# Forward the SessionEnd payload (stdin) straight through to the CLI hook.
# env=env is REQUIRED — without it the child inherits the unmodified os.environ
# and the setdefault()s above are silently ignored.
subprocess.run(
    ["uv", "tool", "run", "claude-code-transcripts", "hook"],
    stdin=sys.stdin,
    env=env,
    check=False,
)
