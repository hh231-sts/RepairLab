# RepairLab · 研发工单多 Agent 平台

本地单用户工程作品：保存工单与代码版本，通过 Agent 循环定位、复现和修复问题，在全新 Docker 环境独立验收，交付补丁、证据和执行轨迹。

**默认关闭真实模型调用。** 脚本化模式无需模型密钥。配置本机 `.env` 后，可显式使用 `-EnableModelCalls` 启动真实模式，在界面创建工单并选择 DeepSeek；见[日常操作说明](docs/daily-workflow.md)。默认启动和自动化验证使用明确标记的替身，embedding 保持关闭；正式 benchmark 成绩仍待后续实验。

## 启动

前提：Python 3.12、uv、Node.js 20+、Docker Desktop / Docker Engine；Docker 必须能运行 Linux 容器。首次依赖安装和镜像构建需要网络，任务执行容器没有网络。

Windows PowerShell，在项目目录执行：

```powershell
./scripts/start.ps1
# 已有沙箱镜像时：./scripts/start.ps1 -SkipImageBuild
# 已配置密钥与价格、需要真实模型时：
./scripts/start.ps1 -EnableModelCalls -SkipImageBuild -SkipSetup
```

WSL/Linux：

```bash
bash scripts/start.sh
```

打开 **http://localhost:5173**。API 文档：**http://127.0.0.1:8000/docs**。API 与 worker 为独立进程；PostgreSQL/pgvector 通过 Compose 运行。启动脚本默认关闭真实模型，只有显式参数才启用；embedding 继续关闭，不做模型连通性探测。

界面点击“导入本地开发夹具”，在工单页发起 `single` 或 `adaptive` 脚本化运行。`repair` 生成正确修复；`empty`、`wrong`、`injection` 用于检查拒绝行为。它们驱动真实账本、调度、MCP、Docker 和独立验证，不代表模型能力。

Windows 停止应用：`./scripts/stop.ps1`。保留数据库和执行产物；需要停止数据库时执行 `docker compose stop db`。Linux 启动脚本可用 Ctrl+C 结束。

## 手工运行

复制 `.env.example` 为 `.env`，保持两个模型开关为 false。数据库端口默认只绑定本机。API 使用 `.env` 中的 `API_TOKEN`，前端可通过“连接设置”修改本地 token。

```bash
uv sync --frozen --extra dev
docker compose up -d --wait db
docker build -f docker/sandbox.Dockerfile -t repairlab-sandbox:local .
uv run python -c "from repairlab.config import Settings; Settings().prepare()"
uv run alembic upgrade head
uv run uvicorn repairlab.api:create_app --factory --host 127.0.0.1 --port 8000
# 另一个终端
uv run repairlab worker
# 再一个终端
cd frontend
npm ci
npm run dev
```

未配置 `DATABASE_URL` 时使用 SQLite 开发后备和持久 SQLite checkpoint。正式本地部署与并发验收使用 PostgreSQL；SQLite 测试结果不替代 PostgreSQL 集成验证。

## 已实现

- 项目固定 commit 快照、文本/符号/文档检索、独立文档版本、工单材料内容与哈希快照。
- LangGraph 循环与持久 checkpoint；PostgreSQL 业务账本、并发领取、心跳、执行租约、旧执行者隔离。
- 动作前意图记录、稳定动作 ID、重复结果复用、写入哈希对账、按租约重建工作区、暂停/恢复/取消/重试。
- 四种内部策略、四类 Agent 职责；最多两个并发子任务、四个不同子任务；产物与工具证据验收、显式补丁集成。
- 父子共用调用数、时间和费用预算；调用前费用预占；缺失 usage 保留预占；全局最高 2000 元预算池。
- Docker 只读挂载、无网络、非 root、资源限制；干净环境验证；拒绝空补丁、错误补丁、过期验证与伪造交付。
- MCP stdio 检索服务和官方客户端；PostgreSQL FTS、pgvector、RRF 融合；确定性向量替身与禁用的真实 E5 Adapter。
- 经验来源/版本/状态/失效管理、回归门槛、冻结快照；四个版本化 Skills。
- SSE 续读、结构化事件、本地 OpenTelemetry JSONL、补丁/产物/费用/轨迹导出；实验批次与报告。
- React/TypeScript 页面连接真实 API，显示环境错误、模型禁用、失败与部分交付。

## 验证与资料

```bash
uv run pytest -m "not integration"
uv run ruff check backend tests migrations scripts
uv run mypy backend/repairlab
cd frontend
npm run typecheck
npm run build
npm run test:e2e
```

真实集成测试需预先迁移一个独立 PostgreSQL 测试库，并设置 `TEST_DATABASE_URL`。测试会创建本地记录与容器，不使用模型。Windows 权限环境建议将 pytest `--basetemp` 放在项目的全新 `.cache/` 子目录中。

- [本轮交付与验证记录](docs/verification.md)
- [架构、恢复与权限边界](docs/architecture.md)
- [任务格式、导入与预检](docs/tasks.md)
- [运行、演示与故障处理](docs/runbook.md)
- [接口与模块导航](docs/interfaces.md)
- [后续真实模型验证与实验](docs/future-evaluation.md)
- [能力映射与贡献边界](docs/portfolio.md)

`research/` 保留此前研究原文，仅作为历史背景；其中服务运行排障、故障演练及旧的任务规模建议不属于当前应用范围。**本轮 36 个真实任务入库为 0，108 次正式模型实验为 0。** 数据和实验目标留待后续执行，不能用开发夹具或模拟输出抵充。

后续已补齐[真实模式和日常界面流程](docs/daily-workflow.md)。显式使用 `scripts/start.ps1 -EnableModelCalls` 启动后，可在界面选择 DeepSeek、创建新工单、设置预算及重试；日常无需重复执行 API 命令。默认启动仍禁用真实模型。
