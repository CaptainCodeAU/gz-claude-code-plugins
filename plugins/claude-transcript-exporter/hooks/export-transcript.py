#!/usr/bin/env python3
"""Export Claude Code session transcript on session end."""

import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

DEFAULT_OUTPUT_DIR = os.path.expanduser("~/CODE/my-claude-code-transcripts")
LOG_FILE = os.path.expanduser("~/.claude/logs/transcript-export.log")
VOICE_URL = "http://localhost:8888/notify"
VOICE_ID = "fTtv3eikoepIosk8dTZ5"

SKIP_DIRS = {"projects", "code", "repos", "src", "dev", "work", "documents"}
OS_PREFIXES = ["-home-", "-mnt-c-Users-", "-mnt-c-users-", "-Users-"]


def get_project_display_name(folder_name):
    name = folder_name
    for prefix in OS_PREFIXES:
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):]
            break

    parts = name.split("-")
    meaningful_parts = []
    found_project = False

    for i, part in enumerate(parts):
        if not part:
            continue
        if i == 0 and not found_project:
            remaining = [p.lower() for p in parts[i + 1:]]
            if any(d in remaining for d in SKIP_DIRS):
                continue
        if part.lower() in SKIP_DIRS:
            found_project = True
            continue
        meaningful_parts.append(part)
        found_project = True

    if meaningful_parts:
        return "-".join(meaningful_parts)

    for part in reversed(parts):
        if part:
            return part
    return folder_name


def cwd_to_project_key(cwd):
    return cwd.replace("/", "-").replace("_", "-").replace(".", "-")


def extract_cwd_from_jsonl(transcript_path):
    try:
        with open(transcript_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = entry.get("cwd", "")
                if cwd:
                    return cwd
    except OSError:
        pass
    return ""


def resolve_project_name(transcript_path, payload_cwd):
    # Primary: transcript_path parent directory name
    # This is the ~/.claude/projects/ encoded folder name — the exact same input
    # that the `all` command passes to get_project_display_name(), guaranteeing
    # consistent archive folder names between plugin exports and batch exports.
    parent_name = pathlib.Path(transcript_path).parent.name
    if parent_name and parent_name != "." and parent_name != "/":
        return get_project_display_name(parent_name), "transcript_path"

    # Fallback: cwd from SessionEnd payload
    # Claude Code encodes paths by replacing both / and _ with -
    if payload_cwd:
        project_key = cwd_to_project_key(payload_cwd)
        return get_project_display_name(project_key), "payload_cwd"

    # Fallback: JSONL cwd field
    jsonl_cwd = extract_cwd_from_jsonl(transcript_path)
    if jsonl_cwd:
        project_key = cwd_to_project_key(jsonl_cwd)
        return get_project_display_name(project_key), "jsonl_cwd"

    return "_unresolved", "unresolved"


def notify_macos(title, message):
    try:
        escaped_msg = message.replace('"', '\\"')
        escaped_title = title.replace('"', '\\"')
        subprocess.Popen([
            "osascript", "-e",
            f'display notification "{escaped_msg}" with title "{escaped_title}"',
        ])
    except OSError:
        pass


def notify_voice(message):
    try:
        payload = json.dumps({
            "message": message,
            "voice_id": VOICE_ID,
            "voice_enabled": True,
        })
        subprocess.Popen([
            "curl", "-s", "-X", "POST", VOICE_URL,
            "-H", "Content-Type: application/json",
            "-d", payload,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def log_entry(session_id, project, status, error="", duration_ms=0, source="", cwd=""):
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "session_id": session_id,
        "project": project,
        "status": status,
        "duration_ms": duration_ms,
    }
    if error:
        entry["error"] = error
    if source:
        entry["source"] = source
    if cwd:
        entry["cwd"] = cwd
    try:
        log_dir = os.path.dirname(LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def report(session_id, project, status, error="", duration_ms=0, source="", cwd=""):
    log_entry(session_id, project, status, error, duration_ms, source, cwd)
    if status == "ok":
        notify_macos("Claude Transcripts", f"Session exported → {project}")
        notify_voice(f"Transcript exported to {project}")
    elif status == "skipped":
        notify_macos("Claude Transcripts", f"Session already exported → {project}")
    else:
        reason = error or "unknown error"
        notify_macos("Claude Transcripts", f"Export failed: {reason}")
        notify_voice(f"Transcript export failed. {reason}")


def main():
    if os.environ.get("SKIP_SESSION_END_HOOK") == "1":
        return

    start = time.time()
    session_id = ""
    project = None

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        report("", None, "error", "invalid stdin payload")
        return

    session_id = payload.get("session_id", "")
    transcript_path = payload.get("transcript_path", "")
    payload_cwd = payload.get("cwd", "")

    if not transcript_path or not os.path.isfile(transcript_path):
        report(session_id, None, "error", "transcript file missing")
        return

    if not shutil.which("claude-code-transcripts"):
        report(session_id, None, "error", "CLI not found on PATH")
        return

    project, source = resolve_project_name(transcript_path, payload_cwd)
    resolved_cwd = payload_cwd
    output_dir = os.environ.get("TRANSCRIPT_EXPORT_DIR", DEFAULT_OUTPUT_DIR)
    project_dir = os.path.join(output_dir, project)

    uuid = pathlib.Path(transcript_path).stem
    session_dir = os.path.join(project_dir, uuid)

    os.makedirs(project_dir, exist_ok=True)

    try:
        result = subprocess.run(
            ["claude-code-transcripts", "json", transcript_path, "-o", project_dir, "-a", "--json"],
            timeout=10,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        elapsed = int((time.time() - start) * 1000)
        report(session_id, project, "error", "CLI timed out", elapsed, source, resolved_cwd)
        return
    except OSError as e:
        elapsed = int((time.time() - start) * 1000)
        report(session_id, project, "error", str(e), elapsed, source, resolved_cwd)
        return

    elapsed = int((time.time() - start) * 1000)

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()[:200]
        report(session_id, project, "error", f"CLI exit {result.returncode}: {stderr_text}", elapsed, source, resolved_cwd)
        return

    report(session_id, project, "ok", "", elapsed, source, resolved_cwd)

    open_target = session_dir if os.path.isdir(session_dir) else project_dir
    try:
        subprocess.Popen(["open", open_target])
    except OSError:
        pass


if __name__ == "__main__":
    main()
