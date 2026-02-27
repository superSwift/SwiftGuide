import json
import os
import time
import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://quant:quant123@localhost:5432/quant")
START_DATE = os.getenv("START_DATE", "20100101")
END_DATE = os.getenv("END_DATE", datetime.now().strftime("%Y%m%d"))
ADJUST = os.getenv("ADJUST", "qfq")
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "0.2"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

engine = create_engine(DB_URL, pool_pre_ping=True)

EXCHANGE_MAP = {"sh": "SH", "sz": "SZ", "bj": "BJ"}


def normalize_symbol(raw_code: str) -> str:
    raw_code = str(raw_code).strip()
    if raw_code.startswith(("sh", "sz", "bj")):
        return f"{raw_code[2:]}.{EXCHANGE_MAP[raw_code[:2]]}"
    if raw_code.startswith(("6", "5")):
        return f"{raw_code}.SH"
    if raw_code.startswith(("0", "3")):
        return f"{raw_code}.SZ"
    return f"{raw_code}.BJ"


def load_stock_list() -> pd.DataFrame:
    import akshare as ak

    spot = ak.stock_zh_a_spot_em()
    spot["symbol"] = spot["代码"].astype(str).apply(normalize_symbol)
    spot["name"] = spot["名称"]
    spot["exchange"] = spot["symbol"].str[-2:]
    return spot[["symbol", "name", "exchange"]].drop_duplicates("symbol")


def upsert_stock_basic(df: pd.DataFrame) -> None:
    sql = text(
        """
        INSERT INTO stock_basic(symbol, name, exchange, updated_at)
        VALUES (:symbol, :name, :exchange, NOW())
        ON CONFLICT(symbol) DO UPDATE
        SET name = EXCLUDED.name,
            exchange = EXCLUDED.exchange,
            updated_at = NOW();
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict(orient="records"))


def get_latest_trade_date(symbol: str) -> str:
    query = text(
        """
        SELECT MAX(trade_date) AS dt
        FROM stock_daily
        WHERE symbol = :symbol AND adjust = :adjust
        """
    )
    with engine.begin() as conn:
        row = conn.execute(query, {"symbol": symbol, "adjust": ADJUST}).mappings().first()
    if row and row["dt"]:
        return row["dt"].strftime("%Y%m%d")
    return START_DATE


def fetch_daily(symbol: str, from_date: str) -> pd.DataFrame:
    import akshare as ak

    secid = symbol.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    raw = ak.stock_zh_a_hist(symbol=secid, period="daily", start_date=from_date, end_date=END_DATE, adjust=ADJUST)
    if raw.empty:
        return raw

    raw = raw.rename(
        columns={
            "日期": "trade_date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "pct_chg",
            "涨跌额": "change",
            "换手率": "turnover",
        }
    )
    raw["trade_date"] = pd.to_datetime(raw["trade_date"]).dt.date
    raw["symbol"] = symbol
    raw["adjust"] = ADJUST
    keep_cols = [
        "symbol",
        "trade_date",
        "open",
        "close",
        "high",
        "low",
        "volume",
        "amount",
        "amplitude",
        "pct_chg",
        "change",
        "turnover",
        "adjust",
    ]
    return raw[keep_cols]


def fetch_daily_with_retry(symbol: str, from_date: str) -> pd.DataFrame:
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_daily(symbol, from_date)
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(1.0, SLEEP_SECONDS * attempt))
    raise RuntimeError(f"fetch failed after retries: {last_exc}")


def upsert_daily(df: pd.DataFrame) -> None:
    sql = text(
        """
        INSERT INTO stock_daily(
          symbol, trade_date, open, close, high, low,
          volume, amount, amplitude, pct_chg, change, turnover, adjust, updated_at
        ) VALUES (
          :symbol, :trade_date, :open, :close, :high, :low,
          :volume, :amount, :amplitude, :pct_chg, :change, :turnover, :adjust, NOW()
        )
        ON CONFLICT(symbol, trade_date, adjust) DO UPDATE
        SET open = EXCLUDED.open,
            close = EXCLUDED.close,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            volume = EXCLUDED.volume,
            amount = EXCLUDED.amount,
            amplitude = EXCLUDED.amplitude,
            pct_chg = EXCLUDED.pct_chg,
            change = EXCLUDED.change,
            turnover = EXCLUDED.turnover,
            updated_at = NOW();
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, df.to_dict(orient="records"))


def evaluate_data_quality(adjust: str) -> dict:
    duplicate_sql = text(
        """
        SELECT COALESCE(SUM(cnt - 1), 0) AS duplicate_rows
        FROM (
          SELECT symbol, trade_date, adjust, COUNT(*) AS cnt
          FROM stock_daily
          WHERE adjust = :adjust
          GROUP BY symbol, trade_date, adjust
          HAVING COUNT(*) > 1
        ) t;
        """
    )
    null_sql = text(
        """
        SELECT COUNT(*) AS null_ohlc_rows
        FROM stock_daily
        WHERE adjust = :adjust
          AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL)
        """
    )
    range_sql = text(
        """
        SELECT MIN(trade_date) AS earliest_trade_date, MAX(trade_date) AS latest_trade_date
        FROM stock_daily
        WHERE adjust = :adjust
        """
    )

    with engine.begin() as conn:
        duplicate_rows = conn.execute(duplicate_sql, {"adjust": adjust}).mappings().first()["duplicate_rows"]
        null_rows = conn.execute(null_sql, {"adjust": adjust}).mappings().first()["null_ohlc_rows"]
        date_range = conn.execute(range_sql, {"adjust": adjust}).mappings().first()

    return {
        "duplicate_rows": int(duplicate_rows or 0),
        "null_ohlc_rows": int(null_rows or 0),
        "earliest_trade_date": date_range["earliest_trade_date"],
        "latest_trade_date": date_range["latest_trade_date"],
    }


def write_sync_job(job_id: str, status: str, success_count: int, failed_count: int, message: str | None = None) -> None:
    sql = text(
        """
        UPDATE sync_job_log
        SET status = :status,
            finished_at = CASE WHEN :status IN ('success', 'failed') THEN NOW() ELSE finished_at END,
            success_count = :success_count,
            failed_count = :failed_count,
            message = :message,
            updated_at = NOW()
        WHERE job_id = :job_id
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "job_id": job_id,
                "status": status,
                "success_count": success_count,
                "failed_count": failed_count,
                "message": message,
            },
        )


def create_sync_job() -> str:
    job_id = uuid.uuid4().hex[:20]
    sql = text(
        """
        INSERT INTO sync_job_log(job_id, started_at, status, success_count, failed_count)
        VALUES (:job_id, NOW(), 'running', 0, 0)
        """
    )
    with engine.begin() as conn:
        conn.execute(sql, {"job_id": job_id})
    return job_id


def write_quality_report(job_id: str, quality: dict) -> str:
    report_id = uuid.uuid4().hex[:20]
    sql = text(
        """
        INSERT INTO data_quality_report(
          report_id, job_id, adjust, checked_at,
          duplicate_rows, null_ohlc_rows, latest_trade_date, earliest_trade_date, detail_json
        ) VALUES (
          :report_id, :job_id, :adjust, NOW(),
          :duplicate_rows, :null_ohlc_rows, :latest_trade_date, :earliest_trade_date, CAST(:detail_json AS JSONB)
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "report_id": report_id,
                "job_id": job_id,
                "adjust": ADJUST,
                "duplicate_rows": quality["duplicate_rows"],
                "null_ohlc_rows": quality["null_ohlc_rows"],
                "latest_trade_date": quality["latest_trade_date"],
                "earliest_trade_date": quality["earliest_trade_date"],
                "detail_json": json.dumps(quality, ensure_ascii=False, default=str),
            },
        )
    return report_id


def main() -> None:
    job_id = create_sync_job()
    stock_df = load_stock_list()
    upsert_stock_basic(stock_df)
    print(f"任务 {job_id} 启动，总股票数: {len(stock_df)}")

    ok = 0
    failed = 0
    try:
        for idx, row in stock_df.iterrows():
            symbol = row["symbol"]
            try:
                last_day = get_latest_trade_date(symbol)
                daily = fetch_daily_with_retry(symbol, last_day)
                if not daily.empty:
                    upsert_daily(daily)
                ok += 1
                if ok % 100 == 0:
                    print(f"已处理 {ok} 只股票")
            except Exception as exc:
                failed += 1
                print(f"[{symbol}] 同步失败: {exc}")
            time.sleep(SLEEP_SECONDS)

        quality = evaluate_data_quality(ADJUST)
        report_id = write_quality_report(job_id, quality)
        write_sync_job(job_id, "success", ok, failed, message=f"quality_report={report_id}")
        print(f"同步完成，成功: {ok}, 失败: {failed}, 质量报告: {report_id}")
    except Exception as exc:
        write_sync_job(job_id, "failed", ok, failed, message=str(exc))
        raise


if __name__ == "__main__":
    main()
