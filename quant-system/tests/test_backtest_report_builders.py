from api.main import _build_backtest_failure_report, _build_backtest_success_report


def test_build_success_report_shape():
    task = {"strategy_id": "s1", "start_date": "2024-01-01", "end_date": "2024-12-31"}
    report = _build_backtest_success_report(
        task,
        "t1",
        {"avg_return": 0.1, "symbol_count": 10},
        trading_days=240,
        expected_symbols=10,
    )
    assert report["status"] == "success"
    assert report["task_id"] == "t1"
    assert report["metrics"]["avg_return"] == 0.1
    assert report["sample_size"] == 10
    assert report["trading_days"] == 240
    assert report["data_coverage"] == 1.0


def test_build_failure_report_shape():
    task = {"strategy_id": "s1", "start_date": "2024-01-01", "end_date": "2024-12-31"}
    report = _build_backtest_failure_report(task, "t2", "no data", trading_days=0, expected_symbols=10)
    assert report["status"] == "failed"
    assert report["error_code"] == "QS-422-NO-MARKET-DATA"
    assert report["reason"] == "no data"
    assert report["sample_size"] == 0
