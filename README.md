# VendFill 售货机补货

按货道容量、库存与在途量计算缺口，生成不超缺口、非负的补货单。
支持按商品名登记「同品合计补量上限」：同一商品名的多条货道共享一个合计上限，
生成时按货道编号顺序累加，触顶后后续货道补量置 0（原因：同品合计已满，与单道满仓分开统计）。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4800 |
| API | http://localhost:9800 |
| API 文档 | http://localhost:9800/docs |
| Postgres | localhost:5449 |

健康检查：`GET http://localhost:9800/api/health`

## 使用说明

1. 在「点位」「货道」查看售货机布局与库存。
2. 在「点位」页维护各商品的同品合计补量上限（正整数；≤0 拒绝登记；改后重新生成即按新合计截断）。
3. 在「销量」了解近期出货。
4. 打开「补货单」按缺口生成建议补货量。
5. 在「满仓」「汇总」查看已满货道与补货合计（含同品合计触顶行数）。

## 开发与测试

```bash
docker compose exec api pytest -q
```
