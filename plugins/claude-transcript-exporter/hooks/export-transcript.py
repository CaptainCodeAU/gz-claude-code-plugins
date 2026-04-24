#!/usr/bin/env python3
"""Export Claude Code session transcript on session end."""

import json
import os
import pathlib
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
        result = subprocess.run(
            ["claude-code-transcripts", "json", transcript_path, "-o", output_dir, "-a", "--json"],
            timeout=10,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        return

    if result.returncode == 0:
        session_dir = os.path.join(output_dir, pathlib.Path(transcript_path).stem)
        open_target = session_dir if os.path.isdir(session_dir) else output_dir
        subprocess.Popen(["open", open_target])


if __name__ == "__main__":
    main()
