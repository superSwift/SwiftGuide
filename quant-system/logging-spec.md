# Logging Spec v1

## 1. 目标

- 可追踪：能定位一次回测任务从创建到完成的全过程
- 可审计：保留关键请求、策略版本、时间范围、状态流转

## 2. 最小日志字段

- `timestamp`
- `level`
- `event`
- `strategy_id`（如有）
- `task_id`（如有）
- `status`（如有）
- `message`

## 3. 关键事件

- `strategy.created`
- `strategy.validated`
- `backtest.queued`
- `backtest.transitioned`
- `backtest.executed`
- `backtest.failed`

## 4. 建议

- 统一 JSON 日志格式
- 避免记录敏感信息（秘钥、token）
