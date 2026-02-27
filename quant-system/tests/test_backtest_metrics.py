from api.main import _compute_equal_weight_metrics


def test_compute_equal_weight_metrics_empty():
    result = _compute_equal_weight_metrics([])
    assert result["symbol_count"] == 0
    assert result["avg_return"] == 0.0


def test_compute_equal_weight_metrics_basic_case():
    rows = [
        {"start_close": 10, "end_close": 11},
        {"start_close": 20, "end_close": 22},
    ]
    result = _compute_equal_weight_metrics(rows)
    assert result["symbol_count"] == 2
    assert result["avg_return"] == 0.1
    assert result["annualized_return"] == 1.2
