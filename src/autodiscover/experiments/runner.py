"""Bounded supervisor for a fixed reviewed worker, with macOS Seatbelt defense in depth."""

import json
import math
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import psutil

from autodiscover.config import Limits
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.datasets import fixtures
from autodiscover.orchestrator.durability import canonical


class ExecutionError(RuntimeError):
    pass


def sandbox_command(script: Path, *, python: Path | None = None) -> list[str]:
    # Unknown platforms fail closed until an isolation backend has been implemented and tested.
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise ExecutionError("ISOLATION_BACKEND_UNAVAILABLE")
    executable = (python or Path(sys.executable)).resolve()
    read_paths = [Path(sys.base_prefix).resolve(), Path("/System/Library"), Path("/usr/lib")]
    rules = " ".join(f"(subpath {json.dumps(str(p))})" for p in read_paths)
    profile = (
        '(version 1)(deny default)(import "dyld-support.sb")'
        "(allow process-exec)(allow sysctl-read)"
        "(allow file-read-metadata)(allow file-read* "
        + rules
        + f' (literal {json.dumps(str(script.resolve()))}) (literal "/dev/null"))'
    )
    return [
        "/usr/bin/sandbox-exec",
        "-p",
        profile,
        str(executable),
        "-I",
        "-S",
        str(script.resolve()),
    ]


def preflight(plan: Plan, limits: Limits) -> dict[str, Any]:
    if plan.seconds > limits.max_experiment_seconds:
        raise ExecutionError("TIME_AUTHORITY_EXCEEDED")
    script = Path(__file__).with_name("worker.py")
    sandbox_command(script)
    if not hasattr(signal, "SIGKILL"):
        raise ExecutionError("RESOURCE_CONTROLS_UNAVAILABLE")
    return {
        "authorized": True,
        "plan_id": plan.hypothesis_id,
        "plan_digest": plan.digest,
        "isolation": "trusted-allowlist+macOS-seatbelt",
        "network": False,
        "host_file_content": "runtime/interpreter and fixed worker only",
    }


def run(plan: Plan, limits: Limits, *, replication: int = 0) -> dict[str, Any]:
    preflight(plan, limits)
    request = {
        "algorithm": plan.algorithm,
        "rows": fixtures(plan, replication=replication),
        "cpu_seconds": math.ceil(plan.seconds),
        "memory_mb": plan.memory_mb,
    }
    payload = canonical(request).encode()
    if len(payload) > 2000000:
        raise ExecutionError("INPUT_LIMIT_EXCEEDED")
    command = sandbox_command(Path(__file__).with_name("worker.py"))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="adl-worker-") as directory:
        process = subprocess.Popen(  # noqa: S603 - fixed script and validated numeric/data contract
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=directory,
            env={"PYTHONHASHSEED": "0", "PATH": ""},
            start_new_session=True,
        )
        monitor = psutil.Process(process.pid)
        stdout, stderr = bytearray(), bytearray()
        peak_rss = 0
        try:
            if not (process.stdin and process.stdout and process.stderr):
                raise ExecutionError("WORKER_PIPE_UNAVAILABLE")
            # Input is bounded, but can exceed the OS pipe. Communicate via a selector too.
            with selectors.DefaultSelector() as selector:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    os.set_blocking(pipe.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "input")
                selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                sent = 0
                while selector.get_map():
                    if time.monotonic() - started > plan.seconds:
                        raise ExecutionError("WORKER_TIMEOUT")
                    try:
                        peak_rss = max(peak_rss, monitor.memory_info().rss)
                        if peak_rss > plan.memory_mb * 1024 * 1024:
                            raise ExecutionError("WORKER_MEMORY_LIMIT")
                    except psutil.NoSuchProcess:
                        pass
                    for item, _mask in selector.select(timeout=0.01):
                        if item.data == "input":
                            try:
                                sent += os.write(item.fd, payload[sent : sent + 8192])
                            except BrokenPipeError:
                                sent = len(payload)
                            if sent == len(payload):
                                selector.unregister(item.fileobj)
                                process.stdin.close()
                        else:
                            chunk = os.read(item.fd, 8192)
                            if not chunk:
                                selector.unregister(item.fileobj)
                            else:
                                (stdout if item.data == "stdout" else stderr).extend(chunk)
                            if len(stdout) + len(stderr) > plan.max_output_bytes:
                                raise ExecutionError("WORKER_OUTPUT_LIMIT")
            code = process.wait(timeout=max(0.01, plan.seconds - (time.monotonic() - started)))
            if code != 0:
                # Raw stderr can include file paths/private data: never expose or log it.
                raise ExecutionError("WORKER_FAILED")
            data = json.loads(stdout)
            if not isinstance(data, dict):
                raise ExecutionError("WORKER_INVALID_OUTPUT")
            return {
                "output": data,
                "plan_digest": plan.digest,
                "replication": replication,
                "elapsed_seconds": time.monotonic() - started,
                "peak_rss_bytes": peak_rss,
                "worker_sha256": __import__("hashlib")
                .sha256(Path(__file__).with_name("worker.py").read_bytes())
                .hexdigest(),
                "python_version": sys.version.split()[0],
                "isolation": "macOS-seatbelt",
            }
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            raise ExecutionError("WORKER_TIMEOUT_OR_INVALID_JSON") from None
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            for pipe in (process.stdin, process.stdout, process.stderr):
                if pipe and not pipe.closed:
                    pipe.close()
