#!/usr/bin/env python3
"""Export Claude Code session transcript on session end."""

import json
import os
import shutil
import subprocess
import sys

DEFAULT_OUTPUT_DIR = os.path.expanduser("~/CODE/my-claude-code-transcripts")


def main():
    if os.environ.get("SKIP_SESSION_END_HOOK") == "1":
        return

    if not shutil.which("claude-code-transcripts"):
        return

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    transcript_path = payload.get("transcript_path", "")
    if not transcript_path or not os.path.isfile(transcript_path):
        return

    output_dir = os.environ.get("TRANSCRIPT_EXPORT_DIR", DEFAULT_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    try:
        subprocess.run(
            ["claude-code-transcripts", "json", transcript_path, "-o", output_dir, "-a", "--json"],
            timeout=10,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


if __name__ == "__main__":
    main()
