# Harness、协议、评测和前沿研究证据

核查日：2026-10-31。本文把来源事实、作者实验和本项目的设计推论分开。工程文章已打开正文；论文主要核查作者页面、摘要、版本记录，未声称通读全部附录或复现实验。完整仓库对比见 [03-oss-landscape.md](03-oss-landscape.md)。

## 1. Harness 的稳定价值与可替换部分

Harness 可以理解为把模型变成可运行系统的执行层：组织上下文、调用模型、调度工具和子 Agent、保留状态、处理失败与停止、执行权限策略、记录轨迹并交付产物。OpenAI 官方文档明确区分控制面 harness 和执行面 sandbox；二者的状态及生命周期不必绑定。[F04][F05]

Anthropic 2026-04 的 Managed Agents 工程文章同样把 session（追加记录）、harness 和 sandbox 分开。这支持一个设计判断：可丢弃的 worker/容器应与持久的任务记录分离，恢复不能仅靠模型读一段总结。[F01]

2025 年长期任务实践强调初始化、增量推进和交接产物；2026 年后续文章又展示，模型升级会让部分分段和重置策略变成额外开销。因此，项目深度应包括消融和删除失效策略，而非固定堆叠 planner、reviewer 和反思循环。[F02][F03]

这不要求从零重写所有设施。官方开放 harness、托管 Agent API、图运行时、完整开源 harness 都可以成为底座；个人的可评审贡献应是任务语义、调度策略、权限/副作用控制、验收、评测和改进证据。[F04][F06]

## 2. 多 Agent：需要可测的协作收益

| 一手证据 | 支持的结论 | 不能据此声称的结论 |
|---|---|---|
| Google Research，2026-01，180 种配置研究 [F09] | 任务可分解性和顺序依赖影响拓扑选择；并行任务与顺序任务可能得到相反结果 | “多 Agent 必然优于单 Agent” |
| Anthropic Research 产品工程，2025-06 [F11] | 广度检索适合分工与独立上下文；委托、恢复和预算是实际问题 | 内部研究评测的提升能复制到任意业务或成本条件 |
| MAST 最新公开 v3，2025-10 [F12] | 故障可归入系统设计、Agent 目标/信息不一致、验证等类别 | 改几个角色 prompt 就已解决协作可靠性 |
| Anthropic，多 Agent 研究，2026-08 [F10] | 长期对等协作仍存在从众、认知和目标冲突问题 | 给一群 Agent 开聊天群就能形成可信共识 |

设计推论：默认单 Agent；将独立检索、日志分析、测试设计作为可并行子任务；对共享代码的修改用隔离工作区和明确集成者。子任务有输入、作用域、预算、超时、产物、失败状态和验收条件；返回的“完成”文字不是验收证据。对等 mesh 和投票辩论适合实验分支，不宜先作为默认生产架构。

公平实验至少有三条基线：单 Agent、独立并行后汇总、有受控协作的多 Agent。固定模型、工具、任务和总预算，再比较成功率、成本、延迟、重复劳动、冲突和故障恢复。还应报告等预算与不等预算两种设置的区别，不能把更多 token 的收益全归因于拓扑。

## 3. 上下文工程、程序化工具和记忆

### 上下文

高价值做法包括：相关信息按需检索；压缩旧工具结果；任务状态外置；为子任务建立隔离上下文；保留来源定位和未解决问题。Anthropic 的工程资料把 compaction、结构化笔记与子 Agent 分别用于不同任务形态。[F18]

PTC/CodeAct 路线让代码完成可预测的过滤、连接、聚合和验证，减少大结果反复经过模型。OpenAI 官方指南也明确，单次调用、需要逐步语义判断、审批与证据交付的环节有不同适用方式。[F20] Anthropic 的 MCP 工程文章则说明工具目录和中间结果膨胀带来的上下文成本。[F19]

RLM 把长输入视为外部环境，允许程序化访问及递归子调用，是值得跟踪的推理范式；其公开 v3 为 2026-05。适合作为大仓库/文档任务的对照实验，不应把“理论可处理更长输入”直接写成项目已支持无限上下文。[F21]

### 记忆

| 来源 | 测量重点 | 对个人项目有用的实验 |
|---|---|---|
| MemoryArena，ICML 2026，v2 2026-09 [F27] | 跨会话、相互依赖的行动任务 | 第一次排障经验是否帮助第二次相关问题 |
| DolphinBench，2026-09 [F28] | 历史信息影响工具行动，同时报告成本和延迟 | 记住正确的分支、联系人或工作约束后，行动是否正确 |
| MemDerive，2026-10 预印本 [F29] | 变化历史中的派生状态及依赖 | 代码版本/规则变更后，旧结论是否失效，能否找到支持事件 |

设计推论：把会话记录、当前任务状态、长期经验、文档索引和可执行 skills 分开。先以结构化记录、文件和 BM25/向量混合检索作基线，再测复杂记忆系统；图结构需有实体关系和时序问题作为理由。记录来源、适用仓库/版本、有效时间、权限范围和失效条件。记忆写入不自动成为可信事实；模型总结不覆盖原始测试记录。

## 4. 评测必须成为产品的一部分

Anthropic 的评测方法区分 task、trial、grader 和 trace，建议把代码判定、模型判定、人工校准配合使用。pass@k 关注 k 次至少一次成功；pass^k 关注重复执行均成功，不能混写。[F13]

ICML 2026 的 Agent Reliability 工作强调一致性、扰动稳健性、失败可预测性和安全，说明任务成功率只是一个维度。[F15] 2026-09 的评测可靠性预印本还区分“模型+scaffold 系统表现”和“模型本身能力”；增加同类任务不能消除所有 harness 覆盖不足。[F16]

基础设施会改变分数。Anthropic 的受控实验提示 CPU/RAM 限额、OOM、超时等可能影响结果。[F14] 本项目需要固定镜像、仓库 commit、任务版本、网络条件、资源和模型配置，并把基础设施失败从模型失败中单列。

METR 的 time horizon 是按人类专家完成时间标定的任务难度，不能当作 Agent 自主运行时长；其公开页面 2026-09-08 已注明不再积极更新，也提示较长区间的测量局限。因此不宜用该页面给 2026-10 的模型强弱排名。[F17]

建议测量：任务结果、回归破坏、证据是否支持结论、工具参数/动作正确性、恢复后的终态一致性、外部副作用次数、越权次数、每次成功的成本、P50/P95 延迟、重复运行稳定性、失败类别。LLM judge 主要检查解释质量等语义维度；文件存在、测试通过、数据库状态和网络出口策略应优先确定性检查。

## 5. 协议与开放社区：已核查到 2026 年下半年

| 对象 | 本次核查状态 | 项目采用方式 |
|---|---|---|
| MCP | current 页面为 `2026-07-28`；无状态核心、授权强化；Tasks 在独立扩展；旧特性有迁移/弃用窗口 [F22][F23] | 对工具/数据适配层锁规范和 SDK 版本，测试实际协商；不照搬旧教程的生命周期 |
| A2A | latest specification 标 `1.0.0`，面向独立 Agent 系统间的发现、任务、消息与产物 [F24] | 需要跨进程/跨框架委托时接一条真实互操作链路；内部所有函数不必套协议 |
| Agent Skills | 开放目录格式，按需装载说明、脚本和资源 [F25] | 用于可复用排障/迁移步骤，独立版本与适用条件；格式不等于安全执行权限 |
| AAIF | 2026-10-22 公告接纳 Skills、Open Responses、OpenEnv、OpenSandbox [F26] | 跟踪开放接口和治理变化；不把加入基金会当作性能或成熟度证明 |

MCP 工具互通、A2A 任务委托、Skills 工作知识、sandbox 执行隔离、harness 运行控制分别属于不同层；协议本身不提供完整的业务验收、租户权限和可靠调度。

## 6. 自我改进与 Agent RL：最值得做成加分实验的方向

| 技术线 | 原始证据 | 对本项目的取舍 |
|---|---|---|
| 基于轨迹改进 harness | LangChain 2026-02 工程案例保持模型不变调整 harness [F07]；VS Code 2026-05 描述评测驱动的变更验证 [F08] | 核心：失败聚类 → 版本化候选 → 配对评测 → 接受/拒绝 |
| ACE | ICLR 2026，v3 2026-03：增量整理上下文 playbook [F31] | 适合无需参数训练的经验库实验；保留增删和来源记录 |
| GEPA | 官方仓库以诊断反馈优化 prompt/code [F30] | 可用于工具说明/路由 prompt，固定优化预算和独立验证集 |
| Meta-Harness | 2026-03 论文及作者仓库：外环搜索 harness 代码 [F32] | 在隔离实验分支比较策略；不是让生产 Agent 任意改自己的权限 |
| 自我改进的反证 | 2026-10 预印本发现适应新任务与保留旧能力存在冲突 [F33] | 必须做时间顺序数据流和旧任务回归；展示遗忘与回滚；候选选择用验证集和最终独立测试集分开 |
| SkillForge | 2026-10 v2，论文页面标 NeurIPS 2026：skills 生命周期与训练协同 [F38] | 参考候选、激活、稳定、退役机制；尚未复现，不能继承作者提升数字 |
| Harnessed Agentic RL | Agent Lightning v1.0 官方 2026-10 工程文章 [F34] | 有算力时，用真实部署 harness 采样训练，避免训练时重写一个不同 Agent |
| 开放环境 | OpenEnv 文档提供容器化 reset/step/state、评测和训练路径 [F35] | 把自有任务封装成可复现环境，未来连接训练；文档 main 与 stable 要分开 |

设计推论：一人项目先把端到端效果、数据、奖励和对照做扎实，再决定是否训练。用模型 API 加一段“reflection”不等于完成 RL。对 SFT/DPO/GRPO 只选与目标岗位和算力匹配的一项，报告数据划分、reward 可被钻空子的地方、训练成本以及离线提升是否迁移到冻结测试集。

## 7. 多 Agent 安全的一个前沿问题

CaMeL 研究用可信控制流和能力/数据流约束保护工具动作，适合借鉴运行时约束思路。[F36] 2026-10 的 multi-CaMeL 预印本提出，单 Agent 的保障不能自动跨委托边界组合：下游可能将上游传来的不可信内容重新当成可信指令。[F39]

设计推论：子 Agent 产物携带来源和信任等级，工具审批不能仅由另一个 Agent 的“已同意”文字获得。网页、日志、仓库文件、检索结果和子 Agent 文本都应保留为数据来源；执行器在模型之外检查作用域、权限、网络与副作用。项目应加入来自仓库 README/日志/子任务结果的注入测试，同时测正常任务可用性。

## 8. 一手来源目录

全部访问日期均为 2026-10-31。A-正文表示工程/规范正文已读取；A-摘要表示论文作者页面摘要与版本记录已核查，未复现实验。动态文档未显示发布日期时，不用抓取时间代替。

| ID | 来源与链接 | 日期/版本 | 阅读层级 |
|---|---|---|---|
| F01 | [Anthropic：Scaling Managed Agents](https://www.anthropic.com/research/managed-agents) | 2026-04-08 | A-正文 |
| F02 | [Anthropic：Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | 2025-11-26 | A-正文 |
| F03 | [Anthropic：Harness design for long-running apps](https://www.anthropic.com/research/harness-design-long-running-apps) | 2026-03-24 | A-正文 |
| F04 | [OpenAI Developers：Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform) | 2026-08-19 | A-正文 |
| F05 | [OpenAI 官方文档：Sandbox Agents](https://developers.openai.com/api/docs/guides/agents/sandboxes) | 动态文档 | A-正文 |
| F06 | [OpenAI 官方文档：Agents API](https://developers.openai.com/api/docs/guides/agents-api/overview) | 动态文档 | A-正文 |
| F07 | [LangChain：Improving Deep Agents with harness engineering](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering) | 2026-02-17，历史 TB2 实验 | A-正文 |
| F08 | [VS Code：The Coding Harness Behind GitHub Copilot](https://code.visualstudio.com/blogs/2026/05/15/agent-harnesses-github-copilot-vscode) | 2026-05-15 | A-正文 |
| F09 | [Google Research：Scaling agent systems](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/) | 2026-01-28 | A-正文 |
| F10 | [Anthropic：Patterns and problems in emerging multiagent systems](https://www.anthropic.com/research/multiagent-systems) | 2026-08-13 | A-正文 |
| F11 | [Anthropic：Multi-agent research system](https://www.anthropic.com/research/multi-agent-research-system) | 2025-06-13 | A-正文 |
| F12 | [MAST：Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657v3) | v3 2025-10-26 | A-摘要 |
| F13 | [Anthropic：Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | 2026-01-09 | A-正文 |
| F14 | [Anthropic：Infrastructure noise in agentic coding evals](https://www.anthropic.com/research/infrastructure-noise) | 2026-02-05 | A-正文 |
| F15 | [Towards a Science of AI Agent Reliability](https://arxiv.org/abs/2602.16666v3) | v3 2026-06-02；ICML 2026 | A-摘要 |
| F16 | [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651) | 2026-09-30，预印本 | A-摘要 |
| F17 | [METR：Task-Completion Time Horizons](https://metr.org/time-horizons/) | 最后更新 2026-09-08，停止积极维护 | A-正文 |
| F18 | [Anthropic：Effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | 2025-09-29 | A-正文 |
| F19 | [Anthropic：Code execution with MCP](https://www.anthropic.com/research/code-execution-with-mcp) | 2025-11-04 | A-正文 |
| F20 | [OpenAI 官方文档：Programmatic Tool Calling](https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling) | 动态文档 | A-正文 |
| F21 | [Recursive Language Models](https://arxiv.org/abs/2512.24601v3) | v3 2026-05-11 | A-摘要 |
| F22 | [MCP：Versioning/current](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning) | current 2026-07-28 | A-正文 |
| F23 | [MCP：2026-07-28 发布说明](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | 2026-07-28 | A-正文 |
| F24 | [A2A：latest specification](https://a2a-protocol.org/latest/specification/) | 页面标 latest released 1.0.0 | A-正文关键章节 |
| F25 | [Agent Skills：Specification](https://agentskills.io/specification) | 动态规范 | A-正文 |
| F26 | [AAIF：Four New Projects](https://aaif.io/news/agentic-ai-foundation-announces-four-new-projects) | 2026-10-22 | A-正文 |
| F27 | [MemoryArena](https://arxiv.org/abs/2602.16313v2) | v2 2026-09-17；ICML 2026 | A-摘要 |
| F28 | [DolphinBench](https://dolphinbench.ai/)；[harness guide](https://dolphinbench.ai/run/guide/) | 论文 2026-09-21；动态指南 | A-正文 |
| F29 | [MemDerive](https://arxiv.org/abs/2610.25373) | 2026-10-18，预印本 | A-摘要 |
| F30 | [GEPA 官方仓库](https://github.com/gepa-ai/gepa) | 动态 README | A-README |
| F31 | [ACE](https://arxiv.org/abs/2510.04618v3) | v3 2026-03-29；ICLR 2026 | A-摘要 |
| F32 | [Meta-Harness 论文](https://arxiv.org/abs/2603.28052)；[作者代码](https://github.com/stanford-iris-lab/meta-harness) | 2026-03-30；Harbor 路线标 experimental | A-摘要/README |
| F33 | [Are Self-Evolving Agents Continual Learners?](https://arxiv.org/abs/2610.25858) | 2026-10-19，预印本 | A-摘要 |
| F34 | [Microsoft Research：Agent Lightning v1.0](https://www.microsoft.com/en-us/research/blog/agent-lightning-v1-0-a-3500-line-lightweight-agentic-rl-framework-for-training-agents-with-real-harnesses/) | 2026-10-07 | A-正文 |
| F35 | [Hugging Face：OpenEnv 官方文档](https://huggingface.co/docs/openenv/index) | main；页面另指 stable v0.10.0 | A-正文 |
| F36 | [Google Research：CaMeL 官方代码](https://github.com/google-research/camel-prompt-injection) | 对应 Defeating Prompt Injections by Design | A-README；论文摘要另查 |
| F37 | [SkillsBench 官方 v1.1](https://github.com/benchflow-ai/skillsbench/releases/tag/v1.1) | 2026-06；BenchFlow task.md 格式 | A-release |
| F38 | [SkillForge](https://arxiv.org/abs/2610.09832v2) | v2 2026-10-14；页面标 NeurIPS 2026 | A-摘要 |
| F39 | [Can CaMeLs Talk?](https://arxiv.org/abs/2610.05640) | 2026-10-05，预印本 | A-摘要 |

## 9. 本轮优先级判断（研究者判断，不是厂商结论）

1. 必做：可复现任务环境、可恢复 harness、工具契约、受控并发、产物验收、全链路轨迹和成对评测。
2. 高收益：权限感知混合检索、上下文预算、跨会话记忆与失效、skills 对照、基于失败轨迹的离线改进。
3. 单独实验：PTC/RLM、自适应委托、跨框架 A2A、GEPA/Meta-Harness、Agent RL。每项应回答一个具体问题。
4. 暂缓：全功能个人助理/Agent OS、任意桌面自动化、大规模去中心化 swarm、无验收的在线自修改、缺少业务证据的图记忆。

近期论文适合决定实验方向；稳定的工程与测量能力更适合作为项目主干。没有任何来源能证明某一种框架或一个项目覆盖所有公司的所有 Agent JD。

<!-- generated-source-references -->
[F01]: https://www.anthropic.com/research/managed-agents
[F02]: https://www.anthropic.com/research/effective-harnesses-for-long-running-agents
[F03]: https://www.anthropic.com/research/harness-design-long-running-apps
[F04]: https://developers.openai.com/blog/codex-as-a-platform
[F05]: https://developers.openai.com/api/docs/guides/agents/sandboxes
[F06]: https://developers.openai.com/api/docs/guides/agents-api/overview
[F07]: https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering
[F08]: https://code.visualstudio.com/blogs/2026/05/15/agent-harnesses-github-copilot-vscode
[F09]: https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/
[F10]: https://www.anthropic.com/research/multiagent-systems
[F11]: https://www.anthropic.com/research/multi-agent-research-system
[F12]: https://arxiv.org/abs/2503.13657v3
[F13]: https://www.anthropic.com/research/demystifying-evals-for-ai-agents
[F14]: https://www.anthropic.com/research/infrastructure-noise
[F15]: https://arxiv.org/abs/2602.16666v3
[F16]: https://arxiv.org/abs/2610.00651
[F17]: https://metr.org/time-horizons/
[F18]: https://www.anthropic.com/research/effective-context-engineering-for-ai-agents
[F19]: https://www.anthropic.com/research/code-execution-with-mcp
[F20]: https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling
[F21]: https://arxiv.org/abs/2512.24601v3
[F22]: https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning
[F23]: https://blog.modelcontextprotocol.io/posts/2026-07-28/
[F24]: https://a2a-protocol.org/latest/specification/
[F25]: https://agentskills.io/specification
[F26]: https://aaif.io/news/agentic-ai-foundation-announces-four-new-projects
[F27]: https://arxiv.org/abs/2602.16313v2
[F28]: https://dolphinbench.ai/
[F29]: https://arxiv.org/abs/2610.25373
[F30]: https://github.com/gepa-ai/gepa
[F31]: https://arxiv.org/abs/2510.04618v3
[F32]: https://arxiv.org/abs/2603.28052
[F33]: https://arxiv.org/abs/2610.25858
[F34]: https://www.microsoft.com/en-us/research/blog/agent-lightning-v1-0-a-3500-line-lightweight-agentic-rl-framework-for-training-agents-with-real-harnesses/
[F35]: https://huggingface.co/docs/openenv/index
[F36]: https://github.com/google-research/camel-prompt-injection
[F37]: https://github.com/benchflow-ai/skillsbench/releases/tag/v1.1
[F38]: https://arxiv.org/abs/2610.09832v2
[F39]: https://arxiv.org/abs/2610.05640
