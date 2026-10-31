# 本轮交付与验证记录

核验日期：2026-10-31，Asia/Shanghai。交付为本地单用户研发工单平台，真实模型与 embedding 均关闭。

后续真实试跑的协议兼容修复及最新后端验证见 [DeepSeek protocol 修复记录](fixes/2026-10-31-deepseek-protocol.md)。下表保留首轮模型禁用交付时的验证记录。

混合委托调用修复、真实模型界面入口及预算设置的最新验证见 [日常工作流修复记录](fixes/2026-10-31-mixed-delegation.md)。

## 实际执行结果

| 检查 | 结果 | 原始记录 |
|---|---|---|
| 后端单元、API、协议与状态测试 | 52 通过、1 跳过 | [JUnit](verification/unit-results.xml) |
| PostgreSQL + Docker + MCP 集成 | 16 通过 | [JUnit](verification/integration-acceptance.xml) |
| 前端真实后端端到端流程 | 3 通过、0 flaky | [Playwright JSON](verification/e2e-results.json) |
| Ruff 静态检查 | 通过 | `ruff check backend tests migrations scripts` |
| Mypy | 23 个源文件通过 | `mypy backend/repairlab` |
| TypeScript 类型检查与 Vite 构建 | 通过 | `npm run typecheck`、`npm run build` |
| 真实模型 HTTP 请求检查 | 0 次尝试 | [单测审计](verification/network-audit-unit.json)、[集成审计](verification/network-audit-integration-acceptance.json)、[补充审计](verification/network-audit-integration-extra-pass.json) |

测试使用 Windows Python 3.12.5、Node.js 24.19.0、Docker Desktop Linux engine 29.9.2、真实 PostgreSQL/pgvector。包版本与锁文件 SHA256 见 [机器可读汇总](verification/summary.json)。数据库镜像固定为 `pgvector/pgvector@sha256:7b822b0aac60967beb1ea5e576b8602c94c300a157d187f385ae3e0da199b90a`；沙箱基底 Python 3.12.13-slim 同样固定 digest。

十六项集成已在最终代码上整批执行通过。前端测试连接实际 API 和独立 worker，使用真实 Docker；没有用静态响应伪装后端。测试中额外断开并恢复浏览器网络，检查 SSE 事件重新续读。

单元测试中的 SandboxDouble 只验证 harness 决策与持久状态，不证明代码真的通过 pytest；相关代码执行结论由真实容器集成和前端流程补充验证。DeepSeek 协议测试只使用 `httpx.MockTransport`，其中模拟请求计数独立于真实模型请求。网络审计统计测试进程的 HTTP 调用并拦截非 loopback socket；它不是厂商计费账单或全系统抓包记录。

## 验证过的关键行为

- 固定单 Agent、独立并行、固定协作和自适应委派在同一 harness 运行；真实自适应流程完成四类角色、父级验收和单点集成。
- 正确修复通过干净环境验证；空补丁、错误补丁、伪造子任务交付及越界读请求被拒绝。
- 真实 worker 分别在写入前、写入后结果落库前、结果落库后 cursor 推进前崩溃，新进程接管后只确认一次动作。
- 真实 PostgreSQL 多线程并发领取只有一个持有者，旧租约不能续租或提交新写入；旧代文件变化不能污染新代工作区。
- 丢失工作区后从已确认记录重建；丢失只读执行容器后按稳定动作 ID 对账并重建执行；重复工具结果复用。
- 真实容器取消竞争、超时、无网络、无密钥/socket 挂载和只读工作区检查。
- 修改补丁后不能沿用旧通过结果；环境与验证器哈希变化检查。
- 独立评分同时运行公开回归与隐藏测试；隐藏用例通过但公开行为回归的补丁被拒绝。
- MCP 官方 SDK 的实际 stdio 子进程检索，PostgreSQL FTS/pgvector 与确定性向量融合；跨项目检索和过期经验拒绝。
- 合成数据行的离线导入、参考补丁/空补丁/无效补丁和重复运行六项真实容器预检；不足 36 个真实任务时不能冻结。
- API 提交去重、实验原子启动、费用预占/usage 缺失、预算耗尽、SSE Last-Event-ID、导出和材料快照。

## 环境限制与未执行事项

Windows 账户不能创建 symlink，`test_symlink_escape` 明确跳过，未记为通过。绝对路径、路径上跳、秘密路径和 Windows 路径拒绝测试已通过。

本轮没有在 WSL 用户发行版单独执行启动脚本，没有运行 Harbor CLI，没有加载真实 E5 权重，没有调用真实 DeepSeek，没有运行真实模型 benchmark。36 个真实任务入库数为 **0**，108 次正式实验完成数为 **0**。本轮真实模型费用为 **0 元**，不输出任何模型修复成功率或协作收益结论。

## 页面与交付文件

- [桌面工作台截图](verification/overview.png)
- [执行时间线截图](verification/workspace.png)
- [项目与检索截图](verification/projects.png)
- [手机布局截图](verification/mobile.png)
- [本地完整启动与实际工单冒烟记录](verification/startup-smoke.json)

应用变更包括根工程配置、Python 后端、数据库迁移与冻结 SQL、Docker 配置、React 前端、开发任务包、测试、启动/停止脚本和运行文档。此前研究文档保留原状，不作为当前功能实现证明。
