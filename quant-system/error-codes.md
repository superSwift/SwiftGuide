# Error Codes v1

用于 Headless API 的统一错误码（Week 1 基线）。

## 通用

- `QS-400-VALIDATION`: 请求参数或策略配置校验失败
- `QS-404-STRATEGY`: 策略不存在
- `QS-404-TASK`: 回测任务不存在
- `QS-404-SYNC-JOB`: 同步任务不存在
- `QS-404-QUALITY-REPORT`: 数据质量报告不存在
- `QS-404-SCHEDULE`: 调度计划不存在
- `QS-400-SCHEDULE-INACTIVE`: 调度计划不可触发（非active）
- `QS-400-STATUS-TRANSITION`: 回测任务状态流转非法
- `QS-422-NO-MARKET-DATA`: 回测时间范围内缺少可用行情数据
- `QS-500-INTERNAL`: 未预期系统错误

## 推荐错误响应结构

```json
{
  "error": {
    "code": "QS-404-STRATEGY",
    "message": "strategy not found",
    "details": {}
  }
}
```
