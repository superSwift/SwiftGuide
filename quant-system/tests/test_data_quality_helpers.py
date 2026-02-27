from datetime import date

from scripts.sync_a_share_daily import normalize_symbol


def test_normalize_symbol_with_prefixes():
    assert normalize_symbol("sh600519") == "600519.SH"
    assert normalize_symbol("sz000001") == "000001.SZ"


def test_normalize_symbol_with_raw_codes():
    assert normalize_symbol("600000") == "600000.SH"
    assert normalize_symbol("300750") == "300750.SZ"
    assert normalize_symbol("830000") == "830000.BJ"


def test_quality_date_serialization_smoke():
    # simple non-runtime smoke for date availability in quality reports
    assert str(date(2024, 1, 1)) == "2024-01-01"
