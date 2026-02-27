import pytest
from fastapi import HTTPException

from api.main import _assert_status_transition


@pytest.mark.parametrize(
    "current_status,next_status",
    [
        ("queued", "running"),
        ("queued", "failed"),
        ("running", "success"),
        ("running", "failed"),
        ("success", "success"),
    ],
)
def test_valid_status_transitions(current_status: str, next_status: str):
    _assert_status_transition(current_status=current_status, next_status=next_status)


@pytest.mark.parametrize(
    "current_status,next_status",
    [
        ("queued", "success"),
        ("running", "queued"),
        ("failed", "running"),
        ("success", "failed"),
    ],
)
def test_invalid_status_transitions(current_status: str, next_status: str):
    with pytest.raises(HTTPException):
        _assert_status_transition(current_status=current_status, next_status=next_status)
