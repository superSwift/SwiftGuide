# Config Spec v1

## 环境变量

- `DATABASE_URL`：数据库连接串
- `START_DATE`：数据同步起始日期（脚本）
- `END_DATE`：数据同步结束日期（脚本）
- `ADJUST`：复权参数（`qfq`/`hfq`/`none`）
- `SLEEP_SECONDS`：数据同步节流秒数

## 约束

- `DATABASE_URL` 必须可连通 PostgreSQL
- `ADJUST` 默认 `qfq`
- 生产环境禁止将密码硬编码在仓库文件中

## 配置优先级

1. 环境变量
2. `.env`（未来可加）
3. 代码默认值
