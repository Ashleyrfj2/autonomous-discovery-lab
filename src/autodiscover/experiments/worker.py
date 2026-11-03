"""Reviewed standalone worker. Run by supervisor with -I -S, never import model code."""

import json
import math
import resource
import sys


def main() -> None:
    request = json.loads(sys.stdin.read(2000001))
    # Defense in depth; all values have already passed a stricter parent-side schema.
    if set(request) != {"algorithm", "rows", "cpu_seconds", "memory_mb"}:
        raise ValueError("Invalid worker request")
    if request["algorithm"] not in ("rle", "identity"):
        raise ValueError("Implementation not allowlisted")
    cpu = max(1, min(120, math.ceil(request["cpu_seconds"])))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    memory = max(64, min(256, int(request["memory_mb"]))) * 1024 * 1024
    # Darwin does not provide a usable data/address-space limit here. The mandatory
    # supervisor enforces RSS with psutil; bounded fixtures prevent allocation spikes.
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))

    def deny(event, args):
        if event == "open" or event.startswith(("socket.", "subprocess.", "os.", "ctypes.")):
            raise PermissionError("Worker capability denied")

    sys.addaudithook(deny)
    rows = request["rows"]
    if not isinstance(rows, list) or len(rows) > 300:
        raise ValueError("Too many rows")
    outputs = []
    for row in rows:
        data = row["data"]
        if len(data) > 1024 or any(type(x) is not int or not 0 <= x <= 255 for x in data):
            raise ValueError("Invalid byte data")
        if request["algorithm"] == "identity":
            encoded = data
        else:
            encoded = []
            position = 0
            while position < len(data):
                value, count = data[position], 1
                while (
                    position + count < len(data) and data[position + count] == value and count < 255
                ):
                    count += 1
                encoded.extend([count, value])
                position += count
        outputs.append({"id": row["id"], "encoded": encoded})
    sys.stdout.write(json.dumps({"schema_version": 1, "rows": outputs}, allow_nan=False))


if __name__ == "__main__":
    main()
