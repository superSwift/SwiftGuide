# Runbook v1（运行手册）

## 1. 本地启动

```bash
cd quant-system
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 首次数据同步

```bash
export DATABASE_URL='postgresql+psycopg2://quant:quant123@localhost:5432/quant'
python scripts/sync_a_share_daily.py
```

## 3. 启动 API

```bash
docker compose up -d api
```

## 4. 健康检查

```bash
curl -s http://localhost:8000/health
```

## 5. 常见故障处理

- 数据库连接失败：检查 `DATABASE_URL` 与 `docker compose ps`
- 同步失败率高：调高 `SLEEP_SECONDS` 并重试
- API 无响应：查看 `docker compose logs api`

## 6. 恢复建议

- 每日备份 PostgreSQL
- 保留任务日志与版本信息，便于问题追踪


## 7. 运行基础测试（推荐）

```bash
cd quant-system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

说明：
- 这些测试优先校验策略 schema 与 API 合同，确保接口契约不会无意破坏。


## 8. 备份与恢复演练（Week 4）

```bash
cd quant-system
./ops/backup_db.sh
./ops/restore_db.sh ./backups/<backup_file>.sql.gz
```

说明：
- 备份脚本依赖 `pg_dump`，恢复脚本依赖 `psql`。
- 请先设置 `PGHOST/PGPORT/PGUSER/PGDATABASE` 等环境变量。
