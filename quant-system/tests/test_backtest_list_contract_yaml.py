from pathlib import Path

import yaml


def test_api_contract_has_backtest_list_and_diagnosis_paths():
    contract_path = Path(__file__).resolve().parent.parent / "api-contract.yaml"
    content = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    paths = content["paths"]
    assert "/backtests" in paths
    assert "/backtests/{task_id}/diagnosis" in paths
