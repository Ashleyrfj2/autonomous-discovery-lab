import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from autodiscover.orchestrator.contracts import Stage
from autodiscover.orchestrator.store import StateError, Store


def test_crash_after_commit_before_checkpoint_resumes_without_duplicate(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("interrupted workflow", {})
    script = """
import os, sys
from pathlib import Path
from autodiscover.orchestrator.store import Store
from autodiscover.orchestrator.contracts import Stage
store=Store(Path(sys.argv[1]))
fence=store.claim(sys.argv[2], 'crashed', .05)
store.checkpoint=lambda run: os._exit(73)
store.complete_step(sys.argv[2], owner='crashed', fence=fence, expected=Stage.DISCOVER,
                    version=0, key='discover:0', output={'questions':['measurable question']})
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path), run], check=False)  # noqa: S603
    assert result.returncode == 73
    assert json.loads((tmp_path / "checkpoints" / f"{run}.json").read_text())["run"]["version"] == 0
    time.sleep(0.06)
    recovered = Store(tmp_path)
    fence = recovered.claim(run, "replacement")
    assert recovered.get_run(run)["stage"] == Stage.RESEARCH
    assert len(recovered.outputs(run)) == 1
    original = recovered.complete_step(
        run,
        owner="replacement",
        fence=fence,
        expected=Stage.DISCOVER,
        version=0,
        key="discover:0",
        output={"questions": ["measurable question"]},
    )
    assert original["version"] == 1
    assert len(recovered.outputs(run)) == 1
    recovered.checkpoint(run)
    assert json.loads((tmp_path / "checkpoints" / f"{run}.json").read_text())["run"]["version"] == 1


def test_concurrent_claims_have_one_winner(tmp_path):
    store = Store(tmp_path)
    run = store.create_run("race", {})

    def claim(owner):
        try:
            return store.claim(run, str(owner))
        except StateError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        winners = [v for v in pool.map(claim, range(8)) if v is not None]
    assert len(winners) == 1
