"""Opt-in exact replay of copied historical qualification. Never resume the original."""

import json
import os
from pathlib import Path

import pytest

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.store import SnapshotStore
from autodiscover.research.discovery import replay
from autodiscover.research.session import session_report

BASELINE = json.loads(
    (Path(__file__).parents[1] / "fixtures/discovery/controlled-live-baseline.json").read_text()
)


def test_original_qualification_replays_and_summary_projection_is_direction_bound():
    root = os.environ.get("ADL_CONTROLLED_BASELINE_ROOT")
    if not root:
        pytest.skip("ADL_CONTROLLED_BASELINE_ROOT must point to a COPY of controlled-live")
    with SnapshotStore(Path(root)) as store:
        before = verify_chain(store)
        digest, packet = replay(store, BASELINE["child_id"])
        assert digest == BASELINE["packet_digest"]
        assert packet.usage == BASELINE["usage"]
        assert packet.candidates == [] and packet.critique_coverage == 0
        assert packet.quality_closed_directions is not None
        for index, expected in BASELINE["closed_directions"].items():
            extraction = packet.quality_closed_directions[int(index)].original.extraction
            assert extraction.gap == expected["gap"]
            assert len(extraction.findings) == expected["findings_count"] == 0
        report = session_report(store, BASELINE["session_id"])
        assert report["status"] == "PAUSED"
        assert report["stop_reason"] == "QUALIFICATION_CHECKPOINT"
        notes = report["branches"][0]["direction_notes"]
        for note in notes:
            assert note["question"] == packet.plan.directions[note["direction"]].question
            assert (
                note["gap"]
                == BASELINE["closed_directions"][str(note["direction"])]["effective_gap"]
            )
        assert replay(store, packet.run_id)[0] == digest
        assert verify_chain(store) == before == BASELINE["evidence_anchor"]
