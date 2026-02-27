CREATE TABLE IF NOT EXISTS stock_basic (
  symbol VARCHAR(16) PRIMARY KEY,
  name VARCHAR(64),
  exchange VARCHAR(8),
  list_date DATE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_daily (
  symbol VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  open NUMERIC(12, 4),
  close NUMERIC(12, 4),
  high NUMERIC(12, 4),
  low NUMERIC(12, 4),
  volume NUMERIC(20, 2),
  amount NUMERIC(20, 2),
  amplitude NUMERIC(10, 4),
  pct_chg NUMERIC(10, 4),
  change NUMERIC(12, 4),
  turnover NUMERIC(10, 4),
  adjust VARCHAR(8) DEFAULT 'qfq',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY(symbol, trade_date, adjust)
);

CREATE INDEX IF NOT EXISTS idx_stock_daily_trade_date ON stock_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_stock_daily_symbol_date ON stock_daily(symbol, trade_date DESC);

CREATE TABLE IF NOT EXISTS strategy_config (
  strategy_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  schema_version VARCHAR(16) NOT NULL,
  config_json JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backtest_task (
  task_id VARCHAR(64) PRIMARY KEY,
  strategy_id VARCHAR(64) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'queued',
  report_json JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_backtest_strategy
    FOREIGN KEY(strategy_id)
    REFERENCES strategy_config(strategy_id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_backtest_task_strategy_id ON backtest_task(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_task_status ON backtest_task(status);

CREATE TABLE IF NOT EXISTS sync_job_log (
  job_id VARCHAR(64) PRIMARY KEY,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  status VARCHAR(24) NOT NULL,
  success_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS data_quality_report (
  report_id VARCHAR(64) PRIMARY KEY,
  job_id VARCHAR(64) NOT NULL,
  adjust VARCHAR(8) NOT NULL,
  checked_at TIMESTAMP NOT NULL,
  duplicate_rows INTEGER NOT NULL DEFAULT 0,
  null_ohlc_rows INTEGER NOT NULL DEFAULT 0,
  latest_trade_date DATE,
  earliest_trade_date DATE,
  detail_json JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_quality_job
    FOREIGN KEY(job_id)
    REFERENCES sync_job_log(job_id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quality_job_id ON data_quality_report(job_id);
CREATE INDEX IF NOT EXISTS idx_quality_checked_at ON data_quality_report(checked_at DESC);

CREATE TABLE IF NOT EXISTS run_schedule (
  schedule_id VARCHAR(64) PRIMARY KEY,
  strategy_id VARCHAR(64) NOT NULL,
  schedule_type VARCHAR(16) NOT NULL,
  schedule_value VARCHAR(32) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'active',
  last_run_at TIMESTAMP,
  next_run_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_schedule_strategy
    FOREIGN KEY(strategy_id)
    REFERENCES strategy_config(strategy_id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_schedule_status ON run_schedule(status);
CREATE INDEX IF NOT EXISTS idx_run_schedule_strategy_id ON run_schedule(strategy_id);
