# 混合委托调用与日常界面入口修复

用户的真实 DeepSeek 运行在第四次调用后失败：`delegate may not mix with other tools`。离线回归用例稳定复现了同一个显式策略拦截；旧代码在保存响应、结算 usage 前拒绝整轮混合调用。

修复后保留模型返回的调用顺序，为普通工具和 delegate 分别执行并返回与原 tool_call_id 对应的观察。连续两个 delegate 可以共享原有并发设施；委托也记录稳定动作 ID、执行意图与结果，恢复时复用已确认结果。父子作用域、四个不同子任务、两个并发上限和产物验收保持执行。

响应在动作分发前落库并结算 usage，因此后续委托校验不会让已取得的 usage 丢失。单 Agent 不再向模型提供 delegate 工具；若模型仍请求不允许的委托，会收到明确的工具拒绝结果，其他合法工具仍执行。无权限的子任务不会被创建。

前端新增真实模型选择、后端配置状态、运行级预算和模型错误/计费浏览；新工单可复用同项目环境与验收模板。预算只能降低原工单契约，重试保留本次限制。启动脚本新增显式真实模式参数及快速启动选项，默认模型禁用策略不变。

用户原始失败记录和未知费用预占不做追溯清零，也不自动重试付费调用。本次验证的模型响应均为脚本或内存 HTTP transport，不把这些测试视为真实模型能力证据。

本次验证结果：69 项后端测试通过、1 项 Windows symlink 环境跳过；18 项真实 PostgreSQL/Docker 集成通过；原有界面流程 3 项与新增真实模式入口（模型 HTTP 为替身）1 项通过。Ruff、Mypy、TypeScript、生产构建和 PowerShell 启动语法检查通过。没有自动重启用户的付费 worker 或提交真实重试。

操作见 [日常工单流程](../daily-workflow.md)。记录见 [汇总](../verification/workflow-fix-summary.json)、[后端 JUnit](../verification/workflow-unit-final.xml)、[集成 JUnit](../verification/workflow-integration.xml)、[原有界面流程](../verification/workflow-e2e-scripted.json)、[新增界面流程](../verification/workflow-e2e-mock-real-mode.json)、[新增界面截图（Mock HTTP）](../verification/workflow-mock-real-mode.png)。
