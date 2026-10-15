#!/usr/bin/env python3
"""
Executor. Runs approved actions.

No AI. No judgment. Just executes what's been approved and logged.
It reads approved.jsonl, validates each action, runs the handler, and logs the result.
"""

import json
import os
import sys
import time
import importlib
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(BASE, "..", "guardrails", "approval_queue")
APPROVED = os.path.join(QUEUE, "approved.jsonl")
EXECUTED = os.path.join(QUEUE, "executed.jsonl")
ACTIONS = os.path.join(BASE, "actions")

sys.path.insert(0, BASE)


def _now():
    return datetime.now(timezone.utc).isoformat()


def load_approved():
    if not os.path.exists(APPROVED):
        return []
    with open(APPROVED) as f:
        return [json.loads(l) for l in f if l.strip()]


def already_executed(intent_id):
    if not os.path.exists(EXECUTED):
        return False
    with open(EXECUTED) as f:
        for line in f:
            if line.strip() and json.loads(line).get("id") == intent_id:
                return True
    return False


def execute(intent):
    action_type = intent["action_type"]
    handler_path = os.path.join(ACTIONS, f"{action_type}.py")
    if not os.path.exists(handler_path):
        return {"ok": False, "error": f"No handler for {action_type}"}

    sys.path.insert(0, ACTIONS)
    module = importlib.import_module(action_type)
    return module.run(intent["payload"])


def log_execution(intent, result):
    with open(EXECUTED, "a") as f:
        f.write(json.dumps({
            "id": intent["id"],
            "ts": _now(),
            "action_type": intent["action_type"],
            "payload": intent["payload"],
            "result": result,
        }) + "\n")


def run_once():
    """Process all approved-but-not-executed intents once."""
    from validators import validate
    count = 0
    for intent in load_approved():
        if already_executed(intent["id"]):
            continue
        ok, reason = validate(intent)
        if not ok:
            log_execution(intent, {"ok": False, "error": f"validator: {reason}"})
            print(f"BLOCKED {intent['id']}: {reason}")
            count += 1
            continue
        result = execute(intent)
        log_execution(intent, result)
        print(f"Executed {intent['id']}: {result}")
        count += 1
    return count


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
        return
    print("Executor running. Polling approved.jsonl every 5s. Ctrl-C to stop.")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"executor error: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
