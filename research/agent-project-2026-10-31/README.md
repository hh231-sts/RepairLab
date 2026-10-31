# 面向求职与长期演进的 AI Agent 项目研究

研究基准日：**2026-10-31，Asia/Shanghai**。本轮已完成广泛搜集、证据整理和项目筛选；尚未实施推荐项目，也没有制造效果数据。

## 结论

首选是 **研发工单与故障排查多 Agent 平台 + 可恢复执行 harness + 独立评测与改进闭环**。它把代码/文档/日志检索、工具执行、协作、记忆、状态恢复、权限、观测和成本统一在可验证的任务上。同一底座可替换为客服/采购等业务工单场景。

“尽可能不过时”靠模型和实现可替换、任务与验收可复现、每代模型重新消融，以及持续核对维护状态，无法由某一个框架名称保证。

## 研究范围和证据质量

| 部分 | 本轮实际完成 | 主要边界 |
|---|---|---|
| 国内招聘 | 检索19家公司；9家取得28条具体官方职责材料，A正文9/B索引19；另列1条已下架历史样本 | 字节/蚂蚁/快手等另10家有入口或线索，正文未核实，不混入能力矩阵 |
| 海外招聘 | 13家公司32条具体官方材料，A正文17/B索引15；另记录Meta缺口 | 资深岗偏多；部分动态页/404仅作索引或历史证据 |
| 开源生态 | 50个项目/协议/基准系列，18组深入取舍 | 不是50个全部实测；source-available、托管服务与宽松许可证开源已区分 |
| 工程与研究 | 39组一手工程、协议、论文/项目来源 | 论文主要核查摘要与版本；预印本、厂商内部实验与独立验证分开 |
| 选题与方案 | 6类候选比较、13类JD能力映射、架构、基线/消融、里程碑 | 均为建议，计划任务规模不等于已跑数据 |

合计60条官方岗位材料，来自22家有具体职责证据的公司，26条A、34条B。统计单元不是60个保证现招的岗位，也不是全市场普查。不同来源集合有交叉，不应将岗位、项目与论文数量相加当作独立来源总量。

报告的URL索引共保留205个去重地址，包含一手正文、官方索引、候选链接、历史/失效页面与少量发现线索；这不是“205个全部实读且当前有效的来源”。文档内部链接、来源编号与表格计数已检查，未对全部外部网站做自动实时存活检查。

## 文件导航

| 文件 | 内容 |
|---|---|
| [00-method-and-search-log.md](00-method-and-search-log.md) | 研究方法、检索批次、证据规则与过程发现 |
| [01-china-jd.md](01-china-jd.md) | 国内28条JD表、19家公司覆盖、缺口与能力矩阵 |
| [02-global-jd.md](02-global-jd.md) | 海外32条材料、13家公司、岗位分层及个人项目边界 |
| [03-oss-landscape.md](03-oss-landscape.md) | 50项分层清单、维护/版本/许可、18组深查和shortlist |
| [04-frontier-and-harness.md](04-frontier-and-harness.md) | 39组技术证据：harness、多Agent、context、memory、协议、评测、RL、安全 |
| [05-project-recommendation.md](05-project-recommendation.md) | 最终选题、模块到JD映射、实施顺序、评测和作品集 |
| [sources.json](sources.json) | 从报告提取的去重URL索引，含出现文件与行号；不是额外验证记录 |
| [audit.json](audit.json) | 文档计数、局部链接和来源引用检查；不检查外部网站实时状态 |

快速阅读：先看05的结论、候选比较和JD映射，再按想投的岗位读01/02；技术选型读03，想做研究加分项读04。所有文章与岗位有原始链接，便于复查。

## 最值得关注的证据

- [百度Agent开发实习 J106681](https://talent.baidu.com/jobs/detail/INTERN/162291c8-43e8-4cc0-9c96-3fb0a7ebb720)：工程、skills、eval、trace和成本在一个具体岗位中结合。
- [京东Agent架构开发](https://zhaopin.jd.com/web/job-info-detail?requementId=220462)：中断恢复、并发编排和执行追踪。
- [Anthropic Managed Agents招聘](https://job-boards.greenhouse.io/anthropic/jobs/5395767008)：随模型升级用评测检验harness假设。
- [DeerFlow 2.1](https://github.com/bytedance/deer-flow/releases/tag/v2.1.0)：可验证的子任务产物与父级验收，适合研究协作可靠性。
- [Google agent系统扩展研究](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)：架构收益取决于任务性质，必须保留单Agent对照。
- [Agent Lightning v1.0](https://www.microsoft.com/en-us/research/blog/agent-lightning-v1-0-a-3500-line-lightweight-agentic-rl-framework-for-training-agents-with-real-harnesses/)：2026-10的真实部署harness参与RL训练路线，适合进阶分支。

## 决策价值最高的版本核查

- AutoGen README顶部已声明归档/停止维护，推荐MAF；下方仍遗留旧维护模式文字，以顶部通知为准。[官方README](https://github.com/microsoft/autogen/blob/main/README.md)
- AgentScope Runtime发布归档迁移通知，能力已整合入2.0；通知称将归档，不额外推断GitHub归档标记。[官方通知](https://github.com/agentscope-ai/agentscope-runtime)
- Daytona旧公开core已声明2026-06起停止更新，云产品和其他SDK不据此判定停运。[官方README](https://github.com/daytonaio/daytona)
- 当前需核对 [Terminal-Bench 4.0](https://www.tbench.ai/news/terminal-bench-4-0)、[SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md)、[τ-bench 2.0](https://github.com/sierra-research/tau2-bench/releases/tag/v2.0.0)，不能拼接旧版分数。
- [MCP current](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning)为2026-07-28；[A2A latest](https://a2a-protocol.org/latest/specification/)页面标1.0.0；实现时锁定规范与SDK版本。

## 后续最有价值的动作

先明确求职轨道和可用投入，再选一套runtime做10—20任务的技术验证，决定恢复、工具、国产模型兼容与运行成本能否达标。随后做单Agent可验证闭环，再增加多Agent与一条专长。字节、蚂蚁、快手等招聘缺口可在具备可用浏览器的环境重新补读；已有证据足以支撑本轮选题，不需要把未核验文本补成事实。
