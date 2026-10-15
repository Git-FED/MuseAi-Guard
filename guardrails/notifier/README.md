# notifier/

Alerts you when an action needs approval.

## Channels

- `stdout` — default, prints to console
- `email` — sends to a clean address (SMTP)
- `push` — POSTs to a webhook you control

## Config

Edit `config.json`. Keep real secrets out of the repo — use environment variables or a gitignored local file.

## Use

```python
from notify import notify

notify("MUSE: action pending", "post to bluesky needs approval")
```

```bash
python3 notify.py "MUSE" "test notification"
```
