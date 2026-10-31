# DeepSeek 响应解析兼容修复

用户首次真实模型运行在一次调用后以 `terminal_reason=protocol` 结束，尚未产生工具记录。原版本没有保存解析阶段或 usage，旧响应无法离线还原；原始失败记录及其费用预占保持不变。

根据 [DeepSeek Chat Completions 官方响应结构](https://api-docs.deepseek.com/api/create-chat-completion/)，构造内存 HTTP 响应后稳定复现两处问题：

- `ModelReply.usage` 原为 `dict[str, int]`，无法接受官方 `prompt_tokens_details`、`completion_tokens_details` 等嵌套统计对象。
- `message.tool_calls` 为 null 时，原适配器直接遍历导致 TypeError。

这两种输入都会产生与用户相同的 protocol 错误；由于旧响应未保存，不能断言原运行具体命中了哪一种。

修复保留 usage 原始明细并校验计费 token 的非负整数约束，将 null 工具列表规范化为空列表。解析失败新增安全诊断：解析阶段、异常类型与 HTTP 状态，不记录 API Key、请求头、响应正文或工具参数原文。

当响应的 usage 已可解析、但工具参数等后续字段不合法时，仍按 usage 结算预占，并记录失败；usage 缺失或不可用时保留预占并标记 `failed_unknown_usage`。不自动重放付费请求，也不将旧预占擅自清零。

本次验证：

- 修复前，两个最小 MockTransport 用例均失败；修复后通过。
- 协议与记账测试 19 项通过。
- 全量后端测试 61 项通过、1 项 Windows symlink 环境跳过。
- 新增真实 PostgreSQL/Docker 集成测试 1 项通过；模型 HTTP 使用内存 MockTransport。验证带嵌套 usage 的多轮工具、费用结算、补丁和独立验收。
- Ruff 与 Mypy 通过。
- 本次修复新增真实模型 HTTP 请求为 0；真实供应商响应的复核需用户重启 worker 后显式新建重试。

原始记录见 [后端测试](../verification/protocol-fix-unit.xml)、[集成测试](../verification/protocol-fix-integration.xml)、[单测网络审计](../verification/network-audit-protocol-fix-unit.json)、[集成网络审计](../verification/network-audit-protocol-fix-integration.json)。

重启 worker 后，通过 `POST /api/runs/{old_run_id}/control/retry` 创建新运行。若再发生模型错误，可在新运行的 `model_calls[].metadata_json.error` 或 `model.error` 事件查看具体解析阶段。
