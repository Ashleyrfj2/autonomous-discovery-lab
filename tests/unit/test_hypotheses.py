import pytest
from pydantic import ValidationError

from autodiscover.hypotheses.engine import Hypothesis, demo_proposal, normalized


def test_falsifiable_contract_dedup_and_parent_reason():
    one = Hypothesis.model_validate(demo_proposal("gaming data"))
    two = Hypothesis.model_validate(
        {**demo_proposal("telemetry"), "question": "A reworded question?"}
    )
    assert one.identity == two.identity
    assert normalized("Repeated  DATA!") == normalized("repeated data")
    for change in (
        {"threshold": float("nan")},
        {"algorithm": "eval(arbitrary_code)"},
        {"parent_id": one.identity},
        {"metric": "overall success"},
    ):
        with pytest.raises(ValidationError):
            Hypothesis.model_validate({**one.model_dump(), **change})
