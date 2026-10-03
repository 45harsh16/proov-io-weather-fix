# log_util.py
# Lightweight logger for the nightly fleet run.

import time

_log_lines: list = []           # module-private; access via log() and flush_log()


def log(message: str) -> None:
    """Append a timestamped *message* to the in-memory buffer and print it."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    _log_lines.append(line)
    print(line)


def flush_log(path: str) -> None:
    """Write buffered log lines to *path* (append mode) then clear the buffer."""
    with open(path, "a") as f:
        for line in _log_lines:
            f.write(line + "\n")
    _log_lines.clear()
