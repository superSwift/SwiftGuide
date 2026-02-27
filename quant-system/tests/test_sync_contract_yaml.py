from pathlib import Path

import yaml


def test_api_contract_has_sync_paths():
    contract_path = Path(__file__).resolve().parent.parent / "api-contract.yaml"
    content = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    paths = content["paths"]
    assert "/sync/jobs" in paths
    assert "/sync/jobs/latest" in paths
    assert "/sync/jobs/{job_id}/quality" in paths
