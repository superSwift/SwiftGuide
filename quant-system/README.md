# A股日线数据底座（数据库 + 数据接口）

这是第一阶段可运行版本：先把 **A股全量日线数据** 拉下来并提供查询接口。

## 包含内容

- `docker-compose.yml`：启动 PostgreSQL + FastAPI
- `db/init.sql`：建表（`stock_basic` / `stock_daily`）
- `scripts/sync_a_share_daily.py`：通过 AkShare 同步 A 股全量日线到 PostgreSQL
- `api/main.py`：提供基础数据查询接口

## 快速开始

```bash
cd quant-system
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 同步全量数据

> 首次全量同步可能较慢（几千只股票 * 多年历史）

```bash
export DATABASE_URL='postgresql+psycopg2://quant:quant123@localhost:5432/quant'
python scripts/sync_a_share_daily.py
```

可选参数：

- `START_DATE`：默认 `20100101`
- `END_DATE`：默认今天
- `ADJUST`：默认 `qfq`（前复权）
- `SLEEP_SECONDS`：默认 `0.2`，用于限速

示例：

```bash
START_DATE=20200101 ADJUST=qfq SLEEP_SECONDS=0.1 python scripts/sync_a_share_daily.py
```

## 启动数据接口

```bash
docker compose up -d api
```

接口示例：

- `GET /api/v1/health`
- `GET /api/v1/symbols?limit=20&offset=0`
- `GET /api/v1/daily/600519.SH?start_date=2024-01-01&end_date=2024-12-31&adjust=qfq`
- `POST /api/v1/strategies`
- `POST /api/v1/strategies/{strategy_id}/validate`
- `POST /api/v1/backtests/run`
- `POST /api/v1/backtests/{task_id}/transition`
- `POST /api/v1/backtests/{task_id}/execute`
- `GET /api/v1/backtests`
- `GET /api/v1/backtests/{task_id}/diagnosis`
- `POST /api/v1/runs/schedule`
- `GET /api/v1/runs/schedule`
- `POST /api/v1/runs/trigger`
- `GET /api/v1/sync/jobs`
- `GET /api/v1/sync/jobs/latest`
- `GET /api/v1/sync/jobs/{job_id}/quality`

## 可行性说明（你问的重点）

可以做到 A 股全量日线同步，方案可行。

- 数据来源：AkShare（免费，覆盖面较好）
- 存储：PostgreSQL 足够承载日线级别数据
- 精度：日线（OHLCV + 成交额 + 涨跌幅等）
- 更新方式：每天跑一次增量同步（脚本已支持按最后日期续传）

## 下一步建议

1. 增加交易日历与停牌处理
2. 增加财务数据表（季频）
3. 在 API 增加策略筛选端点（按PE/ROE/均线）


## 架构讨论（先系统，后策略）

如果你当前更希望“先搭系统，不急着写策略”，请先看：

- `open-source-platform-evaluation.md`

该文档重点说明：

- 哪些开源项目更适合 A 股
- 是否应直接用现成平台，还是组合式搭建
- 如何先支持“手动编辑策略 + 回测运行”
- 如何后续接入“自然语言 -> 策略JSON”


## 如果放弃图形界面（AI优先模式）

如果你希望把精力集中在“高质量内核 + 可扩展接口”，可采用无 GUI 架构：

- `ai-first-headless-architecture.md`

该方案重点：

- 用 API + 策略 JSON 代替可视化页面
- 用 AI 协助自然语言生成/修订策略
- 强化回测可复现与数据口径一致性


## 分阶段升级策略（先无图形，后图形化）

你的规划非常合理：先跑通无图形系统，后续再升级图形化 UI。

- 详细路线见：`upgrade-roadmap.md`

这份路线图重点保证：

- 当前阶段专注高质量内核
- 后续 UI 通过复用 API 快速接入
- 同时为风控、模型、实盘等扩展预留接口


## 企业级推进方式（分工+里程碑）

如果你希望按企业级方法“明确你我工作并分步推进”，请看：

- `enterprise-delivery-plan.md`

该文档包含：

- 你与我的职责边界（业务Owner / 技术Owner）
- 第一个月按周里程碑与验收标准
- 需求->开发->验收的协作流程


## Week 1 交付物（已启动）

根据企业级推进计划，已先落地以下治理资产：

- `BRD.md`
- `api-contract.yaml`
- `strategy-schema.json`
- `runbook.md`
- `changelog.md`

这些文件用于先冻结需求/接口/策略结构，再进入下一步开发。


## 协作说明：每次操作后的进展播报

你提的这个要求已采用：从现在开始我每次完成一轮操作后，都会给你一个“非技术化简报”，至少包含：

1. **这次做了什么**（1~3条）
2. **现在系统到哪一步了**（对应里程碑）
3. **下一步准备做什么**

这样你不需要懂代码，也能持续掌握项目进度。


## 策略与回测接口（Week 1+）

当前已提供最小闭环接口（无GUI）：

1. 创建策略配置（JSON）
2. 校验策略配置（schema）
3. 提交回测任务（当前为队列占位，便于后续接入回测引擎）
4. 查询任务状态与报告

这让我们可以先把“接口契约+流程”跑通，再逐步替换成真实回测执行器。


补充：回测任务当前已支持状态流转（queued/running/success/failed），便于先跑通任务生命周期。


补充：已增加最小回测执行器接口，可直接执行任务并返回基础收益指标（用于先跑通流程）。


## Week 1 状态：✅ 已完成

本周目标（BRD/API合同/策略Schema/日志规范/错误码规范/配置规范）已完成并入库。

- `BRD.md`
- `api-contract.yaml`
- `strategy-schema.json`
- `logging-spec.md`
- `error-codes.md`
- `config-spec.md`


## Week 2 目标（进行中）

已启动数据稳定化建设：

- 同步任务重试机制（`MAX_RETRIES`）
- 同步作业日志（`sync_job_log`）
- 数据质量报告（`data_quality_report`）

目标是让数据同步过程可追踪、可复盘。


## Week 2 状态：✅ 已完成

已完成数据稳定化与可观测性闭环：

- 同步失败重试机制
- 同步作业日志接口
- 数据质量报告与查询接口

你现在可直接通过 API 查看“最近同步是否健康”。


## Week 3 目标（进行中）

已启动策略与回测闭环增强：

- 回测任务列表与诊断接口
- 失败任务标准化诊断报告
- 回测报告字段标准化


## Week 3 状态：✅ 已完成（回测闭环增强）

已完成回测闭环增强：

- 回测任务列表接口
- 回测任务诊断接口
- 回测报告标准化（sample_size / trading_days / data_coverage）
- 无行情数据失败诊断报告


## Week 4 目标（进行中）

已启动运行与运维基线：

- 调度计划接口（创建/查询/触发）
- 备份与恢复脚本（ops）
- 运维手册补充
