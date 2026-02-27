import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from jsonschema import ValidationError, validate
from pydantic import BaseModel, field_validator
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://quant:quant123@localhost:5432/quant")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

schema_path = Path(__file__).resolve().parent.parent / "strategy-schema.json"
STRATEGY_SCHEMA = json.loads(schema_path.read_text(encoding="utf-8"))
ALLOWED_BACKTEST_STATUS = {"queued", "running", "success", "failed"}
ALLOWED_STATUS_TRANSITIONS = {
    "queued": {"running", "failed"},
    "running": {"success", "failed"},
    "success": set(),
    "failed": set(),
}

app = FastAPI(title="A股日线数据接口", version="0.3.0")


class StrategyConfigPayload(BaseModel):
    name: str
    schema_version: str
    universe: dict[str, Any]
    fundamental: dict[str, Any] | None = None
    technical: dict[str, Any] | None = None
    rebalance: dict[str, Any]
    risk: dict[str, Any]


class BacktestRunPayload(BaseModel):
    strategy_id: str
    start_date: date
    end_date: date


class BacktestTransitionPayload(BaseModel):
    status: str
    report: dict[str, Any] | None = None

    @field_validator("status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in ALLOWED_BACKTEST_STATUS:
            raise ValueError(f"unsupported status: {value}")
        return value


class SchedulePayload(BaseModel):
    strategy_id: str
    schedule_type: str
    schedule_value: str

    @field_validator("schedule_type")
    @classmethod
    def check_schedule_type(cls, value: str) -> str:
        if value not in {"daily", "weekly"}:
            raise ValueError("schedule_type must be daily or weekly")
        return value


def _validate_strategy(payload: dict[str, Any]) -> None:
    try:
        validate(instance=payload, schema=STRATEGY_SCHEMA)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=_error_detail("QS-400-VALIDATION", "strategy validation failed", {"reason": exc.message})) from exc




def _error_detail(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}

def _assert_status_transition(current_status: str, next_status: str) -> None:
    if next_status == current_status:
        return
    if next_status not in ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail=_error_detail("QS-400-STATUS-TRANSITION", "invalid backtest status transition", {"from": current_status, "to": next_status}),
        )


def _compute_equal_weight_metrics(price_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not price_rows:
        return {"symbol_count": 0, "avg_return": 0.0}

    returns = []
    for row in price_rows:
        start_close = float(row["start_close"])
        end_close = float(row["end_close"])
        if start_close <= 0:
            continue
        returns.append((end_close - start_close) / start_close)

    if not returns:
        return {"symbol_count": 0, "avg_return": 0.0}

    avg_return = sum(returns) / len(returns)
    return {
        "symbol_count": len(returns),
        "avg_return": round(avg_return, 6),
        "annualized_return": round(avg_return * 12, 6),
    }


def _load_strategy_config(strategy_id: str) -> dict[str, Any]:
    sql = text("SELECT config_json FROM strategy_config WHERE strategy_id = :strategy_id")
    with engine.begin() as conn:
        row = conn.execute(sql, {"strategy_id": strategy_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-STRATEGY", "strategy not found"))
    return row["config_json"]


def _build_backtest_success_report(
    task: dict[str, Any],
    task_id: str,
    metrics: dict[str, Any],
    trading_days: int,
    expected_symbols: int,
) -> dict[str, Any]:
    return {
        "strategy_id": task["strategy_id"],
        "task_id": task_id,
        "start_date": str(task["start_date"]),
        "end_date": str(task["end_date"]),
        "engine": "minimal-equal-weight-v1",
        "status": "success",
        "metrics": metrics,
        "sample_size": int(metrics.get("symbol_count", 0)),
        "trading_days": trading_days,
        "data_coverage": round((int(metrics.get("symbol_count", 0)) / expected_symbols), 6) if expected_symbols > 0 else 0.0,
        "finished_at": datetime.utcnow().isoformat(),
    }


def _build_backtest_failure_report(
    task: dict[str, Any],
    task_id: str,
    reason: str,
    trading_days: int,
    expected_symbols: int,
) -> dict[str, Any]:
    return {
        "strategy_id": task["strategy_id"],
        "task_id": task_id,
        "start_date": str(task["start_date"]),
        "end_date": str(task["end_date"]),
        "engine": "minimal-equal-weight-v1",
        "status": "failed",
        "error_code": "QS-422-NO-MARKET-DATA",
        "reason": reason,
        "sample_size": 0,
        "trading_days": trading_days,
        "data_coverage": 0.0 if expected_symbols > 0 else 0.0,
        "finished_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/health")
def health() -> dict:
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/v1/symbols")
def symbols(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    sql = text(
        """
        SELECT symbol, name, exchange
        FROM stock_basic
        ORDER BY symbol
        LIMIT :limit OFFSET :offset
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(sql, {"limit": limit, "offset": offset}).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.get("/api/v1/daily/{symbol}")
def daily(
    symbol: str,
    start_date: date,
    end_date: date,
    adjust: str = Query("qfq", pattern="^(qfq|hfq|none)$"),
) -> dict:
    db_adjust = "" if adjust == "none" else adjust
    sql = text(
        """
        SELECT symbol, trade_date, open, close, high, low,
               volume, amount, amplitude, pct_chg, change, turnover, adjust
        FROM stock_daily
        WHERE symbol = :symbol
          AND trade_date BETWEEN :start_date AND :end_date
          AND adjust = :adjust
        ORDER BY trade_date
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {
                "symbol": symbol.upper(),
                "start_date": start_date,
                "end_date": end_date,
                "adjust": db_adjust,
            },
        ).mappings().all()
    return {"symbol": symbol.upper(), "count": len(rows), "items": [dict(row) for row in rows]}


@app.post("/api/v1/strategies", status_code=201)
def create_strategy(payload: StrategyConfigPayload) -> dict:
    config = payload.model_dump()
    _validate_strategy(config)

    strategy_id = uuid.uuid4().hex[:16]
    sql = text(
        """
        INSERT INTO strategy_config(strategy_id, name, schema_version, config_json, updated_at)
        VALUES (:strategy_id, :name, :schema_version, CAST(:config_json AS JSONB), NOW())
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "strategy_id": strategy_id,
                "name": payload.name,
                "schema_version": payload.schema_version,
                "config_json": json.dumps(config, ensure_ascii=False),
            },
        )
    return {"strategy_id": strategy_id, "status": "created"}


@app.get("/api/v1/strategies")
def list_strategies() -> dict:
    sql = text(
        """
        SELECT strategy_id, name, schema_version, created_at, updated_at
        FROM strategy_config
        ORDER BY created_at DESC
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(sql).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.get("/api/v1/strategies/{strategy_id}")
def get_strategy(strategy_id: str) -> dict:
    sql = text(
        """
        SELECT strategy_id, name, schema_version, config_json, created_at, updated_at
        FROM strategy_config
        WHERE strategy_id = :strategy_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"strategy_id": strategy_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-STRATEGY", "strategy not found"))
    return dict(row)


@app.post("/api/v1/strategies/{strategy_id}/validate")
def validate_strategy(strategy_id: str) -> dict:
    sql = text("SELECT config_json FROM strategy_config WHERE strategy_id = :strategy_id")
    with engine.begin() as conn:
        row = conn.execute(sql, {"strategy_id": strategy_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-STRATEGY", "strategy not found"))

    _validate_strategy(row["config_json"])
    return {"strategy_id": strategy_id, "valid": True}


@app.post("/api/v1/backtests/run", status_code=202)
def run_backtest(payload: BacktestRunPayload) -> dict:
    _load_strategy_config(payload.strategy_id)

    task_id = uuid.uuid4().hex[:20]
    report = {
        "note": "backtest engine not integrated yet",
        "created_at": datetime.utcnow().isoformat(),
        "strategy_id": payload.strategy_id,
    }
    insert_sql = text(
        """
        INSERT INTO backtest_task(task_id, strategy_id, start_date, end_date, status, report_json, updated_at)
        VALUES (:task_id, :strategy_id, :start_date, :end_date, 'queued', CAST(:report_json AS JSONB), NOW())
        """
    )
    with engine.begin() as conn:
        conn.execute(
            insert_sql,
            {
                "task_id": task_id,
                "strategy_id": payload.strategy_id,
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "report_json": json.dumps(report, ensure_ascii=False),
            },
        )
    return {"task_id": task_id, "status": "queued"}


@app.post("/api/v1/backtests/{task_id}/transition")
def transition_backtest(task_id: str, payload: BacktestTransitionPayload) -> dict:
    get_sql = text("SELECT status, report_json FROM backtest_task WHERE task_id = :task_id")
    with engine.begin() as conn:
        row = conn.execute(get_sql, {"task_id": task_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-TASK", "task not found"))

    current_status = row["status"]
    next_status = payload.status
    _assert_status_transition(current_status=current_status, next_status=next_status)

    report_json = payload.report if payload.report is not None else row["report_json"]
    update_sql = text(
        """
        UPDATE backtest_task
        SET status = :status,
            report_json = CAST(:report_json AS JSONB),
            updated_at = NOW()
        WHERE task_id = :task_id
        """
    )
    with engine.begin() as conn:
        conn.execute(
            update_sql,
            {
                "task_id": task_id,
                "status": next_status,
                "report_json": json.dumps(report_json, ensure_ascii=False),
            },
        )
    return {"task_id": task_id, "from": current_status, "to": next_status}



@app.post("/api/v1/backtests/{task_id}/execute")
def execute_backtest(task_id: str) -> dict:
    task_sql = text(
        """
        SELECT task_id, strategy_id, start_date, end_date, status
        FROM backtest_task
        WHERE task_id = :task_id
        """
    )
    with engine.begin() as conn:
        task = conn.execute(task_sql, {"task_id": task_id}).mappings().first()
    if not task:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-TASK", "task not found"))

    _assert_status_transition(task["status"], "running")
    transition_backtest(task_id, BacktestTransitionPayload(status="running"))

    strategy = _load_strategy_config(task["strategy_id"])
    hold_count = int(strategy.get("rebalance", {}).get("hold_count", 10))
    expected_symbols = hold_count
    adjust = "qfq"

    trading_days_sql = text(
        """
        SELECT COUNT(DISTINCT trade_date) AS trading_days
        FROM stock_daily
        WHERE trade_date BETWEEN :start_date AND :end_date
          AND adjust = :adjust
        """
    )

    price_sql = text(
        """
        WITH picked AS (
            SELECT symbol
            FROM stock_daily
            WHERE trade_date = :start_date
              AND adjust = :adjust
            ORDER BY symbol
            LIMIT :hold_count
        )
        SELECT p.symbol,
               s.close AS start_close,
               e.close AS end_close
        FROM picked p
        JOIN stock_daily s ON s.symbol = p.symbol AND s.trade_date = :start_date AND s.adjust = :adjust
        JOIN stock_daily e ON e.symbol = p.symbol AND e.trade_date = :end_date AND e.adjust = :adjust
        """
    )
    with engine.begin() as conn:
        trading_days_row = conn.execute(
            trading_days_sql,
            {
                "start_date": task["start_date"],
                "end_date": task["end_date"],
                "adjust": adjust,
            },
        ).mappings().first()
        rows = conn.execute(
            price_sql,
            {
                "start_date": task["start_date"],
                "end_date": task["end_date"],
                "adjust": adjust,
                "hold_count": hold_count,
            },
        ).mappings().all()

    trading_days = int((trading_days_row or {}).get("trading_days") or 0)
    price_rows = [dict(r) for r in rows]
    if not price_rows:
        report = _build_backtest_failure_report(
            task,
            task_id,
            "no overlapping market data for selected date range",
            trading_days=trading_days,
            expected_symbols=expected_symbols,
        )
        transition_backtest(task_id, BacktestTransitionPayload(status="failed", report=report))
        return {"task_id": task_id, "status": "failed", "report": report}

    metrics = _compute_equal_weight_metrics(price_rows)
    report = _build_backtest_success_report(task, task_id, metrics, trading_days=trading_days, expected_symbols=expected_symbols)
    transition_backtest(task_id, BacktestTransitionPayload(status="success", report=report))
    return {"task_id": task_id, "status": "success", "report": report}



@app.get("/api/v1/backtests")
def list_backtests(limit: int = Query(20, ge=1, le=200), status: str | None = Query(default=None)) -> dict:
    base_sql = """
        SELECT task_id, strategy_id, start_date, end_date, status, created_at, updated_at
        FROM backtest_task
    """
    params: dict[str, Any] = {"limit": limit}
    if status:
        base_sql += " WHERE status = :status "
        params["status"] = status
    base_sql += " ORDER BY created_at DESC LIMIT :limit "

    with engine.begin() as conn:
        rows = conn.execute(text(base_sql), params).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.get("/api/v1/backtests/{task_id}/diagnosis")
def backtest_diagnosis(task_id: str) -> dict:
    sql = text("SELECT status, report_json FROM backtest_task WHERE task_id = :task_id")
    with engine.begin() as conn:
        row = conn.execute(sql, {"task_id": task_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-TASK", "task not found"))

    report = row["report_json"] or {}
    return {
        "task_id": task_id,
        "status": row["status"],
        "diagnosis": {
            "has_error": row["status"] == "failed",
            "error_code": report.get("error_code"),
            "reason": report.get("reason"),
        },
    }



@app.post("/api/v1/runs/schedule", status_code=201)
def create_schedule(payload: SchedulePayload) -> dict:
    _load_strategy_config(payload.strategy_id)

    schedule_id = uuid.uuid4().hex[:16]
    sql = text(
        """
        INSERT INTO run_schedule(
          schedule_id, strategy_id, schedule_type, schedule_value, status, created_at, updated_at
        ) VALUES (
          :schedule_id, :strategy_id, :schedule_type, :schedule_value, 'active', NOW(), NOW()
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "schedule_id": schedule_id,
                "strategy_id": payload.strategy_id,
                "schedule_type": payload.schedule_type,
                "schedule_value": payload.schedule_value,
            },
        )
    return {"schedule_id": schedule_id, "status": "active"}


@app.get("/api/v1/runs/schedule")
def list_schedules(limit: int = Query(20, ge=1, le=200)) -> dict:
    sql = text(
        """
        SELECT schedule_id, strategy_id, schedule_type, schedule_value, status,
               last_run_at, next_run_at, created_at, updated_at
        FROM run_schedule
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.post("/api/v1/runs/trigger")
def trigger_schedule_run(schedule_id: str = Query(...)) -> dict:
    sql = text(
        """
        SELECT schedule_id, strategy_id, status
        FROM run_schedule
        WHERE schedule_id = :schedule_id
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"schedule_id": schedule_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-SCHEDULE", "schedule not found"))
    if row["status"] != "active":
        raise HTTPException(status_code=400, detail=_error_detail("QS-400-SCHEDULE-INACTIVE", "schedule is not active"))

    task = BacktestRunPayload(
        strategy_id=row["strategy_id"],
        start_date=date.today().replace(day=1),
        end_date=date.today(),
    )
    queued = run_backtest(task)
    update_sql = text(
        """
        UPDATE run_schedule
        SET last_run_at = NOW(),
            updated_at = NOW()
        WHERE schedule_id = :schedule_id
        """
    )
    with engine.begin() as conn:
        conn.execute(update_sql, {"schedule_id": schedule_id})
    return {"schedule_id": schedule_id, "task": queued}


@app.get("/api/v1/sync/jobs")
def list_sync_jobs(limit: int = Query(20, ge=1, le=200)) -> dict:
    sql = text(
        """
        SELECT job_id, started_at, finished_at, status, success_count, failed_count, message, updated_at
        FROM sync_job_log
        ORDER BY started_at DESC
        LIMIT :limit
        """
    )
    with engine.begin() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@app.get("/api/v1/sync/jobs/latest")
def latest_sync_job() -> dict:
    sql = text(
        """
        SELECT job_id, started_at, finished_at, status, success_count, failed_count, message, updated_at
        FROM sync_job_log
        ORDER BY started_at DESC
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-SYNC-JOB", "sync job not found"))
    return dict(row)


@app.get("/api/v1/sync/jobs/{job_id}/quality")
def sync_job_quality(job_id: str) -> dict:
    job_sql = text("SELECT 1 FROM sync_job_log WHERE job_id = :job_id")
    report_sql = text(
        """
        SELECT report_id, job_id, adjust, checked_at, duplicate_rows, null_ohlc_rows,
               latest_trade_date, earliest_trade_date, detail_json
        FROM data_quality_report
        WHERE job_id = :job_id
        ORDER BY checked_at DESC
        LIMIT 1
        """
    )
    with engine.begin() as conn:
        job = conn.execute(job_sql, {"job_id": job_id}).first()
        if not job:
            raise HTTPException(status_code=404, detail=_error_detail("QS-404-SYNC-JOB", "sync job not found"))
        report = conn.execute(report_sql, {"job_id": job_id}).mappings().first()
    if not report:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-QUALITY-REPORT", "quality report not found"))
    return dict(report)


@app.get("/api/v1/backtests/{task_id}/status")
def backtest_status(task_id: str) -> dict:
    sql = text("SELECT task_id, strategy_id, status, created_at, updated_at FROM backtest_task WHERE task_id = :task_id")
    with engine.begin() as conn:
        row = conn.execute(sql, {"task_id": task_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-TASK", "task not found"))
    return dict(row)


@app.get("/api/v1/backtests/{task_id}/report")
def backtest_report(task_id: str) -> dict:
    sql = text("SELECT task_id, report_json FROM backtest_task WHERE task_id = :task_id")
    with engine.begin() as conn:
        row = conn.execute(sql, {"task_id": task_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail=_error_detail("QS-404-TASK", "task not found"))
    return {"task_id": task_id, "report": row["report_json"]}


# Backward-compatible aliases (temporary)
@app.get("/health")
def health_legacy() -> dict:
    return health()


@app.get("/symbols")
def symbols_legacy(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)) -> dict:
    return symbols(limit=limit, offset=offset)


@app.get("/daily/{symbol}")
def daily_legacy(symbol: str, start_date: date, end_date: date, adjust: str = Query("qfq", pattern="^(qfq|hfq|none)$")) -> dict:
    return daily(symbol=symbol, start_date=start_date, end_date=end_date, adjust=adjust)
