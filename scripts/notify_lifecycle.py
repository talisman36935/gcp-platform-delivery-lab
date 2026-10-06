"""Emit one allowlisted lab lifecycle event to Cloud Logging."""

from datetime import datetime, timezone
import argparse
import json
import re
import subprocess
import sys


EVENTS = {
    "created",
    "ready",
    "expiry-warning",
    "teardown-started",
    "teardown-passed",
    "teardown-failed",
}


def entry(project: str, run_id: str, event: str, occurred_at: str) -> dict:
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("project must be an explicit Google Cloud project ID")
    if not re.fullmatch(r"lab-[a-z0-9-]{1,40}", run_id):
        raise ValueError("run_id must use the bounded lab- identifier format")
    if event not in EVENTS:
        raise ValueError("event is not in the lifecycle allowlist")
    timestamp = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("occurred_at must include a timezone")
    return {
        "schema": "portfolio.lifecycle.v1",
        "run_id": run_id,
        "event": event,
        "occurred_at": timestamp.astimezone(timezone.utc).isoformat(),
    }


def publish(project: str, run_id: str, event: str, *, runner=subprocess.run) -> None:
    message = entry(
        project,
        run_id,
        event,
        datetime.now(timezone.utc).isoformat(),
    )
    command = [
        "gcloud", "logging", "write", "portfolio-lifecycle",
        json.dumps(message, separators=(",", ":")),
        "--payload-type=json", "--severity=NOTICE", f"--project={project}",
    ]
    try:
        runner(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("lifecycle event delivery to Cloud Logging failed") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--event", choices=sorted(EVENTS), required=True)
    args = parser.parse_args()
    try:
        publish(args.project, args.run_id, args.event)
    except (ValueError, RuntimeError) as exc:
        print(f"lifecycle notification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
