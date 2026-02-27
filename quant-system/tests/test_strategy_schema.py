import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


@pytest.fixture(scope="module")
def schema():
    schema_path = Path(__file__).resolve().parent.parent / "strategy-schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_strategy_schema_accepts_minimal_valid_payload(schema):
    payload = {
        "name": "weekly_value_demo",
        "schema_version": "1.0.0",
        "universe": {"exclude_st": True, "min_list_days": 250},
        "rebalance": {"freq": "weekly", "hold_count": 10},
        "risk": {"max_position": 0.1},
    }
    validate(instance=payload, schema=schema)


def test_strategy_schema_rejects_missing_required_field(schema):
    payload = {
        "name": "bad_demo",
        "schema_version": "1.0.0",
        "universe": {"exclude_st": True, "min_list_days": 250},
        "risk": {"max_position": 0.1},
    }
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)


def test_strategy_schema_rejects_invalid_rebalance_freq(schema):
    payload = {
        "name": "bad_freq",
        "schema_version": "1.0.0",
        "universe": {"exclude_st": True, "min_list_days": 250},
        "rebalance": {"freq": "hourly", "hold_count": 10},
        "risk": {"max_position": 0.1},
    }
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)
