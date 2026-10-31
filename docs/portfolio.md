# 作品集能力映射与贡献边界

| 能力 | 代码证据 | 可演示内容 |
|---|---|---|
| Agent 应用开发 | models、harness、context、Skills | issue → 工具 → 补丁 → 验收 |
| 平台与恢复 | ledger、receipts、分租约工作区、checkpoint | worker 崩溃、旧租约、重复结果 |
| 协作系统 | policy、delegation、integration | 并行调查、证据验收、单点集成 |
| 检索与知识 | Knowledge、MCP、FTS/pgvector | 源码引用、项目隔离、经验失效 |
| 安全与执行 | SafePath、DockerSandbox、Verifier | 路径越界、无网络、隐藏测试隔离 |
| 产品交付 | FastAPI、React、SSE、导出 | 真实界面与后端全流程 |
| 测试与评测 | unit/integration/e2e、task preflight | 原始/错误/参考补丁区分、真实容器恢复 |

工程实现的可陈述范围：自定义任务契约、业务账本、权限与副作用语义、费用预占、委托验收、补丁版本绑定、知识管理、任务导入和产品交互。LangGraph 图执行与 checkpoint 底座、MCP SDK、FastAPI、SQLAlchemy、PostgreSQL/pgvector、Docker、React 等属于复用的第三方能力。

本轮代码由编程助手按需求生成并在本机验证。个人简历中的“个人贡献”需要依据你实际复核、修改和演示的工作填写，不把自动生成或第三方组件全部表述为个人从零研发。

当前可以陈述工程验证结果，不能陈述真实模型修复率、正式 SWE-bench 成绩、协作收益、线上生产稳定性或多租户能力。后续效果报告应引用真实导出的逐次结果，避免将计划任务数写成完成量。
