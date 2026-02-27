# AI 优先的无图形界面量化系统方案（A股）

> 结论先行：如果你愿意用 AI 做策略编写/调整，放弃图形界面通常会让系统质量更高、演进更快。

## 1. 为什么“无 GUI + 高质量接口”通常更优

在你的场景下，核心资产不是页面，而是：

1. 数据质量（口径一致、可追溯）
2. 执行内核（可复现、可回放）
3. 接口契约（稳定、可扩展）
4. 回测评估（可信、无未来函数）

GUI 往往会分散大量开发精力（权限、状态管理、前端联调），
而你已经明确可用 AI 协助策略，这意味着优先投入后端能力会更划算。

---

## 2. 推荐架构：Headless Core + AI Copilot

```text
[你 + AI 对话]
      |
      v
[策略DSL/JSON生成器]
      |
      v
[Strategy API] -----> [Backtest Engine]
      |                     |
      v                     v
[Metadata DB]         [Result DB]
      ^                     ^
      |                     |
      +------ [Market Data Service] <---- [AkShare]
```

核心思想：

- 让系统只暴露“清晰 API + 结构化配置”
- AI 负责把自然语言转成策略 JSON/DSL
- 引擎按统一协议执行并产出可审计结果

---

## 3. 建议保留的 5 类高质量接口

## 3.1 Data API（行情/财务）

- `GET /symbols`
- `GET /daily/{symbol}`
- `GET /factors?...`

要求：版本化、分页、字段字典、复权口径固定。

## 3.2 Strategy API（策略配置）

- `POST /strategies` 创建策略
- `GET /strategies/{id}` 查询策略
- `POST /strategies/{id}/validate` 规则校验

要求：策略 schema 强校验（JSON Schema / Pydantic）。

## 3.3 Backtest API（回测任务）

- `POST /backtests/run`
- `GET /backtests/{task_id}/status`
- `GET /backtests/{task_id}/report`

要求：异步任务、可重试、可复现（记录数据版本与参数）。

## 3.4 Execution API（运行调度）

- `POST /runs/schedule`
- `POST /runs/trigger`
- `GET /runs/{id}/logs`

要求：任务幂等、防重复执行、完整日志。

## 3.5 AI Assist API（自然语言转策略）

- `POST /ai/strategy-draft`（NL -> JSON）
- `POST /ai/strategy-revise`（按反馈改策略）

要求：

- 只产出结构化配置，不直接执行交易
- 必须经过 validate 再允许回测

---

## 4. “无 GUI”并不等于“不可用”

你可以用这三层交互替代传统图形界面：

1. **Chat 控制层**：你用自然语言描述策略
2. **配置文件层**：系统维护策略 JSON（可版本管理）
3. **报告层**：输出 Markdown/HTML 回测报告

这样你看到的是“人类可读报告 + 结构化策略”，不是页面按钮。

---

## 5. 质量提升的关键工程实践

1. **严格 schema**：策略字段全部类型化并校验
2. **数据版本化**：回测记录数据快照版本
3. **可复现执行**：任务参数、代码版本、依赖版本全记录
4. **防未来函数**：回测引擎只用当时可得数据
5. **评估标准统一**：收益/回撤/夏普/换手/交易成本统一口径

---

## 6. 你这个方向的风险与应对

风险 1：自然语言有歧义
- 应对：AI 生成后必须经过 schema validate + 人工确认

风险 2：策略改动太频繁
- 应对：策略版本号 + 基线对比报告

风险 3：过拟合
- 应对：样本外 + 滚动窗口 + 参数稳定性检查

---

## 7. 推荐实施节奏（无 GUI 版）

### 第 1 阶段（1~2周）
- 完成 Data API + Strategy API + schema validate

### 第 2 阶段（2~4周）
- 完成 Backtest API + 报告生成 + 任务调度

### 第 3 阶段（4周+）
- 接入 AI Assist API（NL -> 策略JSON）
- 增加策略模板库和自动诊断

---

## 8. 一句话建议

如果你接受“用 AI 对话 + 配置文件 + 报告”作为主要交互方式，
放弃图形界面会让项目更专注、更稳定，也更容易做出高质量内核。
