from pathlib import Path

import yaml


def test_api_contract_has_v1_server_and_core_paths():
    contract_path = Path(__file__).resolve().parent.parent / "api-contract.yaml"
    content = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert content["openapi"] == "3.0.3"
    assert content["servers"][0]["url"] == "/api/v1"

    paths = content["paths"]
    assert "/health" in paths
    assert "/symbols" in paths
    assert "/daily/{symbol}" in paths
    assert "/strategies" in paths
    assert "/backtests/run" in paths
