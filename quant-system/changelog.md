# Changelog

## 2026-02-26

- 新增 `BRD.md`：v1 业务需求范围与验收标准
- 新增 `api-contract.yaml`：v1 OpenAPI 合同草案
- 新增 `strategy-schema.json`：策略配置 schema v1
- 新增 `runbook.md`：运行手册 v1
- 更新 `README.md`：补充 Week 1 交付物入口

- 更新 `README.md`：新增“每次操作后进展播报”的协作约定
- 更新 `api/main.py`：增加 `/api/v1` 路径下策略与回测最小闭环接口，并保留旧路径兼容
- 更新 `db/init.sql`：新增 `strategy_config` 与 `backtest_task` 表
- 更新 `requirements.txt`：新增 `jsonschema` 用于策略校验
- 更新 `README.md`：补充 v1 新接口说明
- 新增 `requirements-dev.txt` 与基础测试（schema/API合同），补齐最小自动化校验
- 更新 `api/main.py`：新增回测任务状态流转接口与状态迁移校验
- 更新 `api-contract.yaml` 与 `README.md`：补充状态流转接口说明
- 新增 `tests/test_backtest_status_transition.py`：覆盖状态迁移规则测试
- 更新 `api/main.py`：新增最小回测执行接口 `/api/v1/backtests/{task_id}/execute`
- 新增 `tests/test_backtest_metrics.py`：覆盖基础收益指标计算逻辑
- 更新 `api-contract.yaml` 与 `README.md`：补充执行接口说明
- 新增 `logging-spec.md`、`error-codes.md`、`config-spec.md`：补齐 Week 1 规范资产
- 更新 `api/main.py`：统一错误响应结构（error code/message/details）
- 更新 `README.md`：标记 Week 1 完成
- 更新 `db/init.sql`：新增 `sync_job_log` 与 `data_quality_report` 表
- 更新 `scripts/sync_a_share_daily.py`：增加重试、作业日志与数据质量报告
- 新增 `tests/test_data_quality_helpers.py`：补充数据质量相关基础测试
- 更新 `README.md`：标记 Week 2 已启动
- 更新 `api/main.py`：新增同步任务与质量报告查询接口（`/api/v1/sync/jobs*`）
- 更新 `api-contract.yaml`、`error-codes.md`、`README.md`：补充 Week 2 接口与错误码
- 更新 `README.md`：标记 Week 2 完成
- 更新 `api/main.py`：新增回测列表与诊断接口，并支持无行情数据失败报告
- 更新 `api-contract.yaml`、`error-codes.md`、`README.md`：补充 Week 3 接口与错误码
- 新增 `tests/test_backtest_report_builders.py`：覆盖回测报告构造逻辑
- 更新 `api/main.py`：回测报告新增标准字段（sample_size/trading_days/data_coverage）
- 更新 `README.md`：标记 Week 3 完成
- 更新 `tests/test_backtest_report_builders.py`：覆盖新增报告字段
- 更新 `db/init.sql`：新增 `run_schedule` 表
- 更新 `api/main.py`：新增调度接口（`/api/v1/runs/schedule`、`/api/v1/runs/trigger`）
- 新增 `ops/backup_db.sh`、`ops/restore_db.sh`：备份与恢复脚本
- 更新 `api-contract.yaml`、`error-codes.md`、`runbook.md`、`README.md`：补充 Week 4 运维能力
- 新增 `tests/test_schedule_contract_yaml.py`：覆盖调度接口契约
