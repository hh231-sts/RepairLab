# Agent 项目选题研究：方法与检索记录

研究基准日：2026-10-31（Asia/Shanghai）。本轮交付为信息收集、证据整理和项目设计建议，尚未实现或实测所建议的项目。

## 目标与默认范围

从国内外互联网/AI 企业官方招聘要求、开源项目及其维护现状、一手工程实践和研究论文出发，寻找个人能完成、能证明能力、便于随模型演进而更新的 Agent 项目。默认优先服务国内 Agent 应用研发/平台工程求职，同时参照国际厂商；算法/Agent RL 是有条件的扩展，不能用一个应用项目替代模型预训练、分布式训练、论文或工作年限要求。

“尽可能不过时”的操作定义是：稳定的接口与可替换实现；可复现的评测和回归；随模型升级重新做消融；核对框架迁移和协议版本。无法保证任何技术永久最新，也不把新发布时间自动等同于成熟度。

## 先广后评的工作顺序

1. 招聘搜集：国内、国际两路独立检索，先记录岗位与证据等级，再归纳能力。
2. 开源搜集：区分编排 runtime、完整 harness、工具协议、执行环境、记忆、观测、训练、benchmark，避免把不同层次当作互斥框架。
3. 技术搜集：补查长期执行、上下文工程、多 Agent 收益与失效、程序化工具调用、安全、记忆行动评测、harness 自我改进及 Agent RL。
4. 新鲜度复核：检索 2026 年下半年信息，打开 releases、迁移/归档公告和规范 current 页，校正旧教程。
5. 交叉评估：把 JD 要求转换为项目中的实现、实验、演示和可检查产物，再比较候选场景。

research 技能要求由背景研究代理收集一手资料，因此使用了三个背景研究任务；主代理补充技术研究并整合结论。各研究文件均以中文释义为主，不全文转载第三方内容。

## 证据口径

- A：直接打开官方具体岗位、仓库/文档、官方工程文章或作者论文页面，读到支持结论的正文。论文只读摘要时另说明阅读深度。
- B：官方域名的搜索索引/摘要提供了具体内容，但直接打开未读到职责正文；属于官方索引快照，不等同于确认现招。
- C：第三方转载、聚合、社区讨论或仅有官方招聘入口/标题。作为发现线索，不能冒充已核实的官方职责。
- 岗位发布日、更新日、搜索抓取日和本轮访问日分开。遇到 404/跳转总页，记录为历史或状态未确认。
- 一个页面有许多岗位标题，不算已核查同等数量的具体 JD。相同岗位不同国家页面/镜像不算独立岗位。
- 招聘样本是定向抽样，不能推断全市场技能出现比例；研究/平台/应用/端侧和资历要求也不能混为同一分母。
- 仓库能力以维护者声称及公开接口为证据，尚未安装实测，不据此证明生产安全、性能或部署可用性。
- 公布的模型/系统分数有模型、预算、环境、任务版本的条件。不同版本/不同 harness 的分数不拼接排名。

## 检索批次与方向

| 批次 | 检索方式/代表查询 | 要解决的问题 |
|---|---|---|
| 招聘广搜 | `site:careers.tencent.com Agent`、`site:zhaopin.meituan.com Harness`，其他企业官方域名，精确岗位名称与 ID | 公司实际要求什么；哪些只是转载 |
| 国际招聘 | 官方 career + Agent Harness/Runtime/Infrastructure/Evals/Applied AI | 应用、平台、训练岗位怎样分工 |
| 工程实践 | `site:anthropic.com engineering harness agents 2026`；`site:developers.openai.com agents harness` | harness 的责任边界和长期任务问题 |
| 新鲜度 | 官方工程目录、仓库 README、releases、archive/migration notice，2026 年 7—10 月信息 | 旧教程是否已经过时 |
| 多 Agent 反证 | Google scaling agent systems；MAST failure taxonomy；Anthropic multiagent systems | 并行/协作何时提高效果、何时增加故障 |
| 评测 | agent reliability、infrastructure noise、Terminal-Bench、SWE-bench Pro、tau-bench | 测什么、怎样避免资源与评分漏洞 |
| 协议与社区 | MCP current/versioning/2026-07-28；A2A latest；Agent Skills；AAIF | 协议版本、互操作与开放治理方向 |
| 记忆 | MemoryArena、DolphinBench、MemDerive、MemoryAgentBench | 是否促进正确行动，怎样处理变更和遗忘 |
| 上下文与工具 | context engineering、RLM、programmatic tool calling、code execution with MCP | 上下文预算、动态工具发现和代码聚合 |
| 改进闭环 | ACE、GEPA、Meta-Harness、self-evolving continual learners | 改进是否可复现，是否使旧任务退化 |
| 训练/环境 | OpenEnv、Agent Lightning v1.0、rLLM、verl | 如何把真实运行轨迹用于训练，个人项目怎样选规模 |
| 安全 | AgentDojo、CaMeL、多 Agent 注入传播、官方 sandbox 文档 | 权限、数据流、工具副作用与执行隔离 |

## 过程中发现并修正的误区

- 不能默认 2025 年流行的 AutoGen/Semantic Kernel 仍是新项目首选；需读 Microsoft Agent Framework 迁移说明。
- 不能把 AgentScope Runtime 与 AgentScope 新主线当作两个必须叠加的组件。
- 不能把云服务在运营等同于其公开核心代码仍活跃开源。
- 搜索根页和旧文档例子的版本可能落后于官方 release；benchmark 要按版本 pin。
- 只比较记忆 QA 分数不足以证明长期任务能力；需评估记忆影响下的行动与失效状态。
- 多 Agent 不是数量越多越好；应与相同模型、工具和预算的单 Agent 及独立并行基线比较。
- “自动自我改进”不意味着可以跳过独立评测；需要旧任务回归、版本记录、失效/回滚机制。

## 阅读导航

- [国内 JD 与证据边界](01-china-jd.md)
- [国际 JD 与岗位分层](02-global-jd.md)
- [开源生态、版本与选型](03-oss-landscape.md)
- [harness、前沿研究与协议证据](04-frontier-and-harness.md)
- [项目筛选、架构和验证方案](05-project-recommendation.md)

最终规模以各报告实际收录清单为准；不把搜索返回条目数当作已读来源数。
