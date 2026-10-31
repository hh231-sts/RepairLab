# 启动、演示与平台运行

## 本轮环境

推荐 Python 3.12 + Node.js + 本地 Docker Linux 容器。WSL/Linux 使用 `scripts/start.sh`；Windows 使用 `scripts/start.ps1`。测试实际在 Windows 的 Python 3.12 与 Docker Desktop Linux engine 上进行；WSL 用户发行版的启动脚本未在本轮单独运行。

启动脚本只绑定本机 8000/5173，数据库只绑定本机 5432。`.env` 不进入代码仓库。默认 API token 仅为本地开发值，可在 `.env` 与前端连接设置中同步更换。真实模型默认关闭，Windows 可用 `-EnableModelCalls` 显式启用；embedding 持续关闭。常规工单操作见[界面流程](daily-workflow.md)。

## 演示路径

1. 工作台导入本地开发夹具，查看固定仓库快照和工单描述。
2. 选择 `single / repair`，查看公开测试原始失败、写入修复、公开测试通过及独立评分。
3. 选择 `adaptive / repair`，查看调查与复现并行、实现子任务、父级验收和显式集成。
4. 运行 `wrong`、`empty`、`injection`，分别查看错误补丁、空补丁、路径上跳请求被拒绝。失败保留部分产物。
5. 发起运行后暂停，等待安全点显示 `paused`，再恢复。重试会创建新 ID；旧记录保留。
6. 导出运行 JSON，包含工单、版本、调用与费用、事件、产物内容及独立验证结果。
7. 知识页创建通用 Skill 新版本，旧运行仍绑定原版本。候选经验需要公开证据、适用版本和两个不同任务的成功回归；单一夹具不能冒充跨任务回归。
8. 实验页创建脚本化策略比较，运行批次和报告始终保留“脚本化测试”标识。

真实进程崩溃演示由 `tests/crash_worker.py` 和集成测试自动执行：分别在写入前、写入后但结果落库前、结果落库后但 cursor 推进前终止进程，过期租约由新 worker 接管。它是测试注入器，不存在生产 HTTP 崩溃开关。

## 检查真实依赖

```powershell
docker version
docker compose ps
docker image inspect repairlab-sandbox:local
```

工作台会显示 Docker 测试镜像是否可用。环境不可用时运行明确失败，不使用宿主执行或测试替身兜底。`SandboxDouble` 只存在于测试目录，通过 Python 依赖注入测试应用，生产配置不能选择它。

## PostgreSQL 集成测试

先创建独立测试库，不能把个人生产数据库作为测试库：

```powershell
docker exec repairlab-db-1 createdb -U repairlab repairlab_test
$env:DATABASE_URL='postgresql+psycopg://repairlab:repairlab@127.0.0.1:5432/repairlab_test'
uv run alembic upgrade head
$env:TEST_DATABASE_URL=$env:DATABASE_URL
$env:NETWORK_AUDIT_FILE='network-audit-integration.json'
uv run pytest tests/test_integration.py -q -p no:cacheprovider --basetemp .cache/pg-test-new
```

`--basetemp` 应指向工作区内新的目录。pytest 会管理这个测试临时目录，不应填写个人文件目录。未设置 `TEST_DATABASE_URL` 时集成测试跳过并说明原因，不能算通过。

## 日志与数据

| 位置 | 内容 |
|---|---|
| PostgreSQL | 业务账本、checkpoint、租约、费用、索引 |
| `data/artifacts` | SHA256 内容寻址产物 |
| `data/snapshots` | 固定仓库快照 |
| `data/workspaces` | 各 Agent 各租约代工作区与临时评分副本 |
| `data/verifiers` | 不挂载给 Agent 的可信验证包 |
| `data/otel.jsonl` | 本地 OpenTelemetry span，无外部 exporter |
| `data/*.log` | Windows 启动脚本的进程日志 |
| `data/task_imports` | 管理员任务导入、预检和筛选清单 |

容器名称为 `repairlab-<动作ID前40位>`。活动或暂停动作的容器用于恢复核查；完成后按记录回收。可检查遗留容器后按具体名称删除；不要清空 Docker 中其他项目的容器或卷。

## 错误处理

- `environment_unavailable`：检查 Docker daemon、context、镜像和宿主目录挂载权限，然后新建重试。补建镜像后重新导入夹具，以冻结正确镜像 ID。
- `model_disabled`：本轮预期行为，不需要提供密钥或开启开关。
- `uncertain_model_call`：真实模型将来启用后可能出现。保留预占费用，人工核对厂商计费记录；不能通过普通 resume 自动重放。可取消旧运行并明确创建新运行。
- `tool_error` / `delegation_rejected`：在工具/产物页检查实际错误和缺失交付，不以 Agent 自述覆盖错误。
- `tests_failed` / `empty_patch`：修复未通过独立验收，保留补丁和失败证据。
- `verifier_version_mismatch` / `environment_version_mismatch`：验证包或镜像与契约不符，不能沿用旧通过结果。
- SSE 断开：前端带 Last-Event-ID 续读。原始事件存于数据库；可直接导出完整轨迹。

仓库快照默认每文件不超过 20 MB、合计不超过 300 MB。保留二进制和原始换行；文本索引跳过非 UTF-8 内容，修复补丁采用 UTF-8 文本修改。超限任务需先评估本机资源，不能静默删除依赖文件后宣称环境完整。
