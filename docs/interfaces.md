# 接口与实现导航

API 的 `/health` 无需 token，其余 `/api/` 接口要求 `Authorization: Bearer <API_TOKEN>`。OpenAPI 可从 `/docs` 浏览；类型模型采用 Pydantic 严格字段检查。任务输入不能改变服务器模型开关、容器权限或工具注册表。

| 接口 | 行为 |
|---|---|
| `GET/POST /api/projects` | 列表、登记本地固定版本仓库并建立索引 |
| `POST /api/projects/{id}/index` | 重建检索；默认不生成向量，确定性测试向量显式命名 |
| `POST /api/projects/{id}/documents` | 保存不可变公开文档版本 |
| `GET /api/projects/{id}/search` | 项目/commit 隔离的文本、符号、向量融合检索 |
| `GET/POST /api/issues` | 不可变工单契约及材料内容快照 |
| `GET/POST /api/runs` | 提交/查询；支持 `Idempotency-Key`，同 key 不同参数拒绝 |
| `GET /api/runs/{id}` | Agent、工具记录、产物、验证、模型账本和费用 |
| `POST /api/runs/{id}/control/{action}` | pause/resume/cancel/retry |
| `POST /api/runs/{id}/input` | 等待输入时追加约束，记录事件并续跑 |
| `GET /api/runs/{id}/events` | SSE；Last-Event-ID / after 续读，follow=false 单批读取 |
| `GET /api/runs/{id}/export` | 输入、轨迹、费用、产物与验收的 JSON 导出 |
| `GET /api/artifacts/{id}` | 用户读取产物内容及 SHA256 响应头 |
| `GET/POST /api/memories` | 查询、创建候选经验 |
| `POST /api/memories/{id}/validate` | 检查两个不同任务的当前补丁回归证据 |
| `POST /api/memories/{id}/invalidate` | 显式失效；已冻结运行也会重新检查失效状态 |
| `GET/POST /api/skills` | 查询和创建不可变新版本 |
| `POST /api/skills/{id}/invalidate` | 停用后续复用 |
| `GET/POST /api/experiments` | 冻结实验配置与经验快照 |
| `POST /api/experiments/{id}/launch` | 原子创建批次，重复提交拒绝 |
| `GET /api/experiments/{id}/report` | 逐运行与逐策略比较；download=true 导出 |
| `POST /api/demo` | 管理员导入本地开发夹具 |
| `GET /api/environment` | 检查本地 Docker 镜像，不探测模型 |
| `GET /api/config` | 返回模型开关、就绪状态与预算上限；不返回密钥 |

新仓库版本通过重新登记固定 commit 创建独立 Project 输入，不就地改写已有快照。SWE-bench 数据、环境构建、参考解预检与冻结使用管理员 CLI，避免把参考解传入普通工单 API 或 Agent。

提交运行可带 `limits`（max_cost_cny、max_calls、max_seconds），仅允许降低工单契约的限制。有效限制保存在 Run 版本清单，恢复和重试沿用。真实模型来源会在入队前检查密钥、价格快照和服务器开关，失败时直接返回配置错误。

## 模块

| 模块 | 职责 |
|---|---|
| `domain.py / db.py` | 任务契约、核心类型、持久账本结构 |
| `ledger.py` | 租约、控制、预算和事件序列 |
| `models.py` | DeepSeek / Scripted / Disabled 接口和错误分类 |
| `harness.py / policy.py` | 持久图循环、固定策略、自适应委托与父级验收 |
| `tools.py` | 参数、作用域、意图、写入对账及长输出产物 |
| `sandbox.py / verification.py` | 实际 Docker 执行、干净环境和验证版本绑定 |
| `storage.py` | 原始字节快照、原子文件、哈希、补丁与工作区重建 |
| `knowledge.py / context.py` | 检索、经验、Skills、约束与证据压缩 |
| `mcp_server.py / mcp_client.py` | 官方 MCP SDK 的 scoped stdio 服务与客户端 |
| `tasks.py` | Harbor 任务导出、离线数据导入、六项入库预检与冻结 |
| `service.py / api.py / worker.py` | 业务事务、HTTP/SSE 和独立 worker |
| `observability.py` | 仅写本地 JSONL 的 OpenTelemetry exporter |
| `frontend/src` | 六类产品页面、运行详情与真实接口交互 |

DeepSeek 工具消息按[官方工具调用协议](https://api-docs.deepseek.com/guides/tool_calls/)保存。固定策略自动执行的集成步骤作为策略观察进入上下文，避免伪造模型发出的工具调用。LangGraph 的[持久 checkpoint](https://docs.langchain.com/oss/python/langgraph/persistence)和业务副作用账本分别负责循环进度与实际动作确认。

embedding 固定为 [multilingual-e5-small revision fd1525a9…](https://huggingface.co/intfloat/multilingual-e5-small/tree/fd1525a9fd15316a2d503bf26ab031a61d056e98)，采用 query/passage 前缀和归一化向量。本轮只验证 Adapter 禁用行为和确定性替身，真实权重未下载/加载。
