#!/usr/bin/env python3
"""
You run this. Approve or deny pending actions.

  python3 approve.py                 # list pending
  python3 approve.py approve <id> [note]
  python3 approve.py deny <id> [note]
"""

import sys
import json
from queue import pending, approve, deny


def main(argv):
    if len(argv) < 2:
        items = pending()
        if not items:
            print("No pending actions.")
            return 0
        for item in items:
            print(f"id:      {item['id']}")
            print(f"type:    {item['action_type']}")
            print(f"reason:  {item['reason']}")
            print(f"payload: {json.dumps(item['payload'])[:300]}")
            print(f"at:      {item['ts']}")
            print("-" * 60)
        return 0

    cmd = argv[1]
    if cmd == "approve":
        if len(argv) < 3:
            print("Need intent id")
            return 1
        note = argv[3] if len(argv) > 3 else ""
        print(json.dumps(approve(argv[2], note), indent=2))
        return 0
    if cmd == "deny":
        if len(argv) < 3:
            print("Need intent id")
            return 1
        note = argv[3] if len(argv) > 3 else ""
        print(json.dumps(deny(argv[2], note), indent=2))
        return 0

    print(f"Unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
