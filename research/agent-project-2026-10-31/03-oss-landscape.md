# AI Agent 开源、运行时、评测与训练生态调研

调研日期：2026-10-31（Asia/Shanghai）。范围：50 个独立项目、协议或基准系列；同一系列的旧仓库与后继仓库合并计数。本文先做分层清单，再进行取舍。没有执行任何项目，也没有实测其性能；官方称“production-ready”的地方仅作为项目自述，不能当作独立验证。

## 证据与筛选方法

- 所有技术事实追溯官方 GitHub 仓库、官方文档、release 或作者发布的 benchmark 页面。搜索结果只用于定位，重要维护状态与版本均实际打开页面复查。
- `R` 表示读取了 README/官方概览；`D` 表示在此基础上复查 release、迁移说明、实现文档或评测协议。超过 15 个条目达到 D。未核验最新 release 的地方明确注明，不以 README 的最近新闻推断其为最新版。
- 许可证只记录已读页面显示的标签或 LICENSE 内容；未核验就记“未核验”。仓库许可证、数据集许可证、任务中第三方软件许可证可能不同。本表也纳入 source-available 和带商业服务的项目，不把它们一律称为宽松许可证开源软件。
- 不以 stars、排行榜单分数或“支持 multi-agent”标签判断项目价值。成本档位、选型结论、项目借鉴点属于本研究的判断，依据是公开接口和本项目需求，并非官方性能承诺。

## 先分层：这些项目不能放在同一张框架排行榜里

| 层次 | 解决的问题 | 例子 | 个人项目要自己证明什么 |
|---|---|---|---|
| 模型与 agent loop SDK | 模型、工具调用、结构化输出、handoff | Agents SDK、Pydantic AI、smolagents、Qwen-Agent | 工具设计、路由、错误处理、基线 |
| 状态执行 runtime / workflow | 状态机、分支、并发、恢复、中断 | LangGraph、MAF、ADK | 幂等、恢复语义、并发边界 |
| 完整 harness / agent 产品 | 上下文、文件、shell、子任务、权限、skills | Deep Agents、DeerFlow、OpenHands SDK、DeepSeek Harness、Pi | 可验证交付、任务账本、预算、安全与可观测 |
| 接入协议 | 跨系统互操作 | A2A；MCP/Agent Skills 由主报告补充 | 确实需要跨服务时才接入，做版本兼容测试 |
| 知识与记忆组件 | 文档检索、跨轮记忆、事实时效与来源 | RAGFlow、Mem0、Graphiti、Letta | 何时写入、更新/撤销、检索收益与污染风险 |
| 环境与隔离 | 文件/命令/浏览器/桌面执行边界 | E2B、OpenSandbox、Browser Use | egress、凭据、租户隔离、资源与生命周期 |
| benchmark / evaluation harness | 任务、环境、评分、轨迹、实验 | Terminal-Bench、SWE-bench、Harbor、Inspect | 固定版本、独立验证器、复现与失败分析 |
| 观测与优化 | traces、数据集、judge、prompt/RL 迭代 | Langfuse、Phoenix、OTel、DSPy、Agent Lightning | 基于数据迭代，而非把日志截图当评测 |

## 广度清单与一手来源

### A. 编排框架、SDK 与运行时（14 项）

| ID | 项目 / 一手来源 | 已核实能力与维护现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O01 | [LangGraph](https://github.com/langchain-ai/langgraph) | D；低层有状态编排，checkpoint/HITL/store；图 runtime，不等于完整 harness | MIT；[releases](https://github.com/langchain-ai/langgraph/releases) 可见 Python 1.2.19，2026-10-30 | 主 runtime 候选；适合明确状态、暂停恢复、可控分支 |
| O02 | [Deep Agents](https://github.com/langchain-ai/deepagents) | D；基于 LangGraph 的完整 harness，文件后端、子 Agent、上下文管理、skills、HITL | MIT；[releases](https://github.com/langchain-ai/deepagents/releases) 列 deepagents 0.7.32；另有独立 code/quickjs 包 | 作为高质量对照基线与源码阅读对象；不要把框架原生功能冒充自研 |
| O03 | [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | D；Python/.NET、图工作流、checkpoint、OTel、HITL、多 provider | [releases](https://github.com/microsoft/agent-framework/releases) Python 1.24.0，2026-10-30；许可证本轮未核验 | Microsoft 生态主候选；同 LangGraph/ADK 选一个主编排层 |
| O04 | [AutoGen README](https://github.com/microsoft/autogen/blob/main/README.md) | D；复核时顶部明确 Project archived and no longer maintained，Microsoft不再提供修复/新功能/支持，推荐迁往MAF；下方仍残留maintenance/community-managed旧文字，以顶部通知为准 | 代码MIT、文档CC BY 4.0（README Legal Notices）；以归档警示为维护判断 | 不作为新项目主底座；用于理解历史multi-agent模式 |
| O05 | [Semantic Kernel](https://github.com/microsoft/semantic-kernel) | D；官方标 MAF 为 successor，给出迁移入口；不是和 MAF 并列的最新首选 | MIT；README 明确 MAF 1.0 production-ready successor | 阅读迁移思路；新项目优先评估 MAF |
| O06 | [Google ADK Python](https://github.com/google/adk-python) | D；2.0 图 runtime、Task API、层级多 Agent、MCP、tool confirmation、可选 A2A | Apache-2.0；[releases](https://github.com/google/adk-python/releases) 可见 2.13.0（notes 2026-10-22） | Google/Gemini 场景强候选；避免照搬 ADK 1.x 教程 API |
| O07 | [OpenAI 官方 Building agents](https://developers.openai.com/tracks/building-agents) | D；Agents SDK 提供 loop、handoff、guardrail、session、tracing；主报告另查托管 Agents API | 本条引用官方文档；SDK 许可证/release 本轮未核验 | 轻量 SDK 路线候选；托管 harness 与自己实现 harness 的能力边界分开写 |
| O08 | [CrewAI](https://github.com/crewAIInc/crewAI) | R；Crews 做角色协作，Flows 做事件驱动确定性编排；商业 control plane 独立 | MIT；最新 release 未核验 | 可快速验证业务流程；深度必须来自任务契约和量化收益 |
| O09 | [Pydantic AI](https://github.com/pydantic/pydantic-ai) | D；typed loop、fallback；独立 Harness/Evals/Graph，OTel instrumentation | MIT；最新 release 未核验 | Python 强类型与可测试工具契约的候选；不是只支持结构化输出的旧定位 |
| O10 | [smolagents](https://github.com/huggingface/smolagents) | R；CodeAgent 把动作写成代码；支持 Docker/E2B/Modal 等执行后端、MCP | Apache-2.0；最新 release 未核验 | 轻量 code-action 基线；不要把解释器白名单当完整隔离 |
| O11 | [Mastra](https://github.com/mastra-ai/mastra) | D；TypeScript agent、图 workflow、HITL、state storage、observational memory | [LICENSE](https://github.com/mastra-ai/mastra/blob/main/LICENSE.md)：主体 Apache-2.0，ee/ 另许可；release 未核验 | TS 全栈候选；与 Python 主栈择一，避免两套编排重复 |
| O12 | [AgentScope 2.0](https://github.com/agentscope-ai/agentscope) | D；ReAct、TeamPipeline、context compaction/offload、权限、memory、sandbox、agent service | Apache-2.0；README 2026-09/10 更新；最新 tag 未核验 | 国内生态主候选，能覆盖应用与服务层；实验性 voice/SOP 要单标 |
| O13 | [AgentScope Runtime](https://github.com/agentscope-ai/agentscope-runtime) | D；Archive Notice：sandbox/AaaS/observability 已并入 AgentScope 2.0，建议迁移，旧仓将只读 | Apache-2.0；归档/迁移告知已核验 | 不再作为独立新依赖引入；避免“AgentScope + Runtime”过时组合 |
| O14 | [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent) | R；Qwen tool use、MCP、code interpreter、RAG；不同模型 tool parser 配置有差异 | Apache-2.0；README 2026-02 Qwen3.5 news，最新 release 未核验 | 作为国产模型工具调用兼容与本地模型基线；README 提示部分 python executor 非 sandbox |

### B. 完整 harness、编码与长期工作产品（8 项）

| ID | 项目 / 一手来源 | 已核实能力与维护现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O15 | [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk/) | D；SDK/Agent Server、typed events、workspace、MCP/skills、远程临时环境；automation/UI 分仓 | MIT；最新 release 未核验 | 编码/修复任务强基线；学习 events / conversations / workspace 分层 |
| O16 | [SWE-agent 官方 docs](https://github.com/SWE-agent/SWE-agent/blob/main/docs/index.md) | D；官方建议 mini-swe-agent，称主要开发投入已转向后者 | 最新 release/许可证本轮未核验 | 不把经典 SWE-agent 名称等同当前主开发路线 |
| O17 | [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | D；小型 issue-solving agent，agent/model/environment 可替换，有轨迹浏览器 | MIT；[releases](https://github.com/SWE-agent/mini-swe-agent/releases) 可见 v2.4.6，7/23 | 必须保留的朴素单 Agent 基线；复杂系统需证明显著收益 |
| O18 | [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | D；everything-is-a-plugin；官方 developer preview，明确可能 breaking changes | MIT；[releases](https://github.com/deepseek-ai/deepseek-harness/releases)：0.2.1-rc.5 10/30，另 0.2.2-alpha.2 10/28 | 插件生命周期、可组合性前沿参考；预发布状态不适合无隔离的核心绑定 |
| O19 | [DeerFlow 2.1.0](https://github.com/bytedance/deer-flow/releases/tag/v2.1.0) | D；可验证工具 receipts、durable batch delegation、memory backend、sandbox、权限 | [repo](https://github.com/bytedance/deer-flow) MIT；2.1.0，2026-09-24 | 对本项目最有价值的源码对照之一：子任务可验证交付，而非只看结论文字 |
| O20 | [Pi](https://github.com/earendil-works/pi) | D；旧 badlogic/pi-mono 现重定向此仓；minimal extensible harness、SDK/RPC/JSON 模式；核心刻意不内置 subagents/plan | MIT；最新 release 未核验 | 自研 harness 的简洁设计参考；不要在 forks 中误读旧包名与维护状态 |
| O21 | [OpenCode](https://github.com/anomalyco/opencode) | R；编码产品，build/plan agent，general subagent；当前安装/文档已走 v2 体系 | MIT；最新 release 未核验 | 作为用户体验与 SDK/permission 设计参照，不必再造通用 IDE |
| O22 | [OpenClaw 官方 docs](https://github.com/openclaw/openclaw/blob/main/docs/index.md) | D；自托管多 channel gateway，session/routing/memory/tools/schedules、trusted gateway 与 untrusted execution 分离 | MIT；[releases](https://github.com/openclaw/openclaw/releases) 多 stable/beta/extended-stable 分支，未断言绝对最新版 | 长期任务与消息接入参照；scope 很宽，个人项目先做单业务闭环 |

### C. 知识、记忆与应用平台（7 项）

| ID | 项目 / 一手来源 | 已核实能力与维护现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O23 | [Dify](https://github.com/langgenius/dify) | R；visual workflows、RAG、agent runtime/skills/MCP、模型管理与观测集成 | 自定义 LICENSE 具体条款本轮未核验；release 未核验 | 业务对照基线/交付平台；只搭画布难以展示自研系统能力 |
| O24 | [RAGFlow](https://github.com/infiniflow/ragflow) | R；复杂文档处理、hybrid retrieval/rerank、agentic RAG、knowledge compilation 与 citations | Apache-2.0；README 载 1.0.0-rc1，2026-09-29；最新 release 未复查 | 知识后端候选；把文档处理、检索与任务运行时分离 |
| O25 | [LlamaIndex](https://github.com/run-llama/llama_index) | D；OSS toolkit 仍可用，README 明确公司重心已转 LlamaParse、LiteParse 与解析/提取评测 | MIT；最新 release 未核验 | 有用的文档生态；不照旧称其公司重心仍是通用 agent orchestration |
| O26 | [Mem0](https://github.com/mem0ai/mem0) | D；user/session/agent memory；2026-04 算法迭代；高分表格明确来自 managed 平台含专有优化 | Apache-2.0 SDK；release 未核验 | memory adapter 候选；不能把商业平台分数写成开源部署复现成绩 |
| O27 | [Letta](https://github.com/letta-ai/letta) / [Letta Code](https://github.com/letta-ai/letta-code) | D；旧仓 README 指活跃源码在 letta-code，V1 API server 在 archive；当前 stateful harness 支持 MemFS/skills/subagents | 两仓页面均标 Apache-2.0；最新 release 未核验 | 长期记忆/自更新上下文参照；避免依赖旧 MemGPT/V1 教程 |
| O28 | [Graphiti / Zep 区分](https://github.com/getzep/graphiti) | D；temporal context graph，实体/关系事实/episode provenance；Graphiti 是建图框架，Zep 为企业 context layer | Graphiti Apache-2.0；Zep 服务不等同此仓，release 未核验 | 对时间变化、来源追踪有明确需求才加图；不为“GraphRAG”标签额外堆栈 |
| O29 | [DSPy](https://github.com/stanfordnlp/dspy) | R；模块化 LM 程序，prompt/weight 优化，RAG/agent loops；README 已提示 native lm15 迁移 | MIT；最新 release 未核验 | 评测稳定后做优化分支；先有数据/指标/held-out，再谈自动优化 |

### D. 执行环境、浏览器与协议（5 项）

| ID | 项目 / 一手来源 | 已核实能力与维护现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O30 | [E2B](https://github.com/e2b-dev/E2B) | R；云隔离 sandbox，Python/TS SDK 控制命令与文件 | Apache-2.0 仓库；服务/基础设施边界另看，release 未核验 | 快速集成环境候选；单独评估配额、持久化与网络策略 |
| O31 | [Daytona](https://github.com/daytonaio/daytona) | D；官方声明 2026-06 core development 迁往私有代码库，公开 core 不再更新/修复/发布 | 历史 LICENSE 具体类型本轮未核验；云服务与 SDK 需另核验 | 可用作云 provider，但不能当作活跃开源 core 首选 |
| O32 | [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) | D；旧 alibaba URL 重定向新组织；Docker 本地/K8s、egress、credential vault、隔离环境生命周期 | Apache-2.0；README 标 AAIF project，最新 release 未核验 | 自托管环境主候选；选定 runtime 后验证真实隔离能力与运维成本 |
| O33 | [Browser Use](https://github.com/browser-use/browser-use) | R；本地 Python library、CLI、cloud/hosted agent 分层，浏览器任务执行 | MIT library；Cloud 不等同开源库，release 未核验 | 浏览器执行 adapter；真实可评测任务优先于开放网“万能演示” |
| O34 | [A2A](https://github.com/a2aproject/A2A) | R；不同系统的 opaque agents 发现能力、协商模态、处理长任务；并非进程内协作 scheduler | Apache-2.0；本轮不深查版本，主报告补 | 仅在跨服务/跨框架交付时加；多 Agent 本身不要求 A2A |

### E. 评测、实验与安全（10 项）

| ID | 项目 / 一手来源 | 已核实内容 / 最新现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O35 | [SWE-bench Verified](https://www.swebench.com/verified) | D；500 人工过滤任务；区分任意系统榜与 mini-swe bash-only；v1/v2 scaffold 成绩不能自动混比 | 数据/代码许可本轮未核验；持续公开榜单 | 编码闭环外部基线；不要只追一个已广泛使用的静态分数 |
| O36 | [SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md) | D；642 任务/11 repo、HARD-51、Harbor 格式；offline agent phase + fresh-sandbox verifier | 官方 root news 9/22 V2；数据/代码许可未分别核验 | 很适合学习防泄漏与独立验证，计算预算较高，可选子集 |
| O37 | [SWE-bench Live](https://github.com/microsoft/SWE-bench-Live) | D；持续构造任务，2026 新增 MultiLang/Windows；8/21 1077 MultiLang、66 Windows；lite/verified 冻结/full 更新 | MIT 仓库；数据集许可另核验；未核验最新 release | 自建“时间上新颖”的测试集和环境构造参考 |
| O38 | [Terminal-Bench 4.0](https://www.tbench.ai/news/terminal-bench-4-0) | D；continuous benchmark；校准资源，移除 8 任务、修复 19；4.1/5.0 页面仍列 upcoming | [官方仓库](https://github.com/harbor-framework/terminal-bench)；4.0.0 数据版本，许可未核验 | terminal/数据/开发任务外部基准；资源配置是实验条件的一部分 |
| O39 | [Harbor](https://github.com/harbor-framework/harbor) | D；evaluation harness，不是产品 agent runtime；统一 agent/environment/task adapter，可生成 RL rollout | Apache-2.0；最新 release 未核验；README 的 TB2 示例不代表当前最新 TB | 自建 benchmark 格式/runner 首选评估对象之一 |
| O40 | [τ-bench 当前 README](https://github.com/sierra-research/tau2-bench/blob/main/README.md) | D；仓库名仍 tau2-bench，但当前 2.0 包含六语言文本/全双工 voice、冻结任务 manifest、diagnostic judges | [2.0.0 release](https://github.com/sierra-research/tau2-bench/releases/tag/v2.0.0)，2026-10-19；许可未核验 | 业务工具调用/政策约束/事务任务首选参照；2.0 与 1.x 不混比 |
| O41 | [OSWorld](https://github.com/xlang-ai/OSWorld) | D；真实桌面任务；2025-07-28 Verified 修订；当前可选 Docker/VM/AWS/Modal/Daytona provider | 许可证/最新 release 未核验 | 电脑使用方向才接入，环境与图形开销高；首版可只做浏览器 |
| O42 | [BrowserGym](https://github.com/ServiceNow/BrowserGym) | R；Gym web environment，包含 WebArena/Verified/WorkArena/TimeWarp 等 | 具体 LICENSE 未核验；release 未核验 | 浏览器环境与产品执行库分开选；每 benchmark 还有独立 setup |
| O43 | [AgentLab](https://github.com/ServiceNow/AgentLab) | R；在 BrowserGym 上开发/并行评测 web agents，Ray、reproducibility utilities、轨迹分析 | 具体 LICENSE/release 未核验 | web 实验 harness 参照；官方明确研究用途，不是现成消费产品 |
| O44 | [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | D；多轮/工具/model graded eval 框架；[security](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/SECURITY.md) 明确 local sandbox 无隔离 | MIT；最新 release 未核验 | 灵活自定义 evaluation 候选；不要把运行模型代码当安全边界 |
| O45 | [AgentDojo](https://github.com/ethz-spylab/agentdojo) | R；prompt injection 攻防动态评测环境；API 仍可能变化 | MIT；最新 release 未核验 | 为工具结果注入等场景建立攻击回归集，而不只跑正常成功任务 |

### F. 可观测、遥测与 Agent RL（5 项）

| ID | 项目 / 一手来源 | 已核实内容 / 维护现状 | 许可证 / 版本证据 | 对个人项目的取舍 |
|---|---|---|---|---|
| O46 | [Langfuse](https://github.com/langfuse/langfuse) | D；traces、prompt management、datasets、code/LLM judge、人类反馈 | MIT 除 ee/；README明确 ee 另许可；release 未核验 | 观测+实验候选；自托管后台资源是额外成本 |
| O47 | [Phoenix](https://github.com/Arize-ai/phoenix) | D；OTel/OpenInference、traces/evals/versioned datasets/experiments | [LICENSE](https://github.com/Arize-ai/phoenix/blob/main/LICENSE)：Elastic License 2.0，非 MIT/Apache；release 未核验 | 轻量起步可评估；不要把 README 的 open-source 自述误写成宽松许可 |
| O48 | [OTel GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) | D；genAI/MCP/provider spans、metrics、events；[旧 docs](https://opentelemetry.io/docs/specs/semconv/gen-ai/) 已明确迁址且旧页不维护 | Apache-2.0；版本/schema 稳定性需按具体 convention 锁定 | 尽早定义标准 trace 字段，避免 vendor-only 记录格式 |
| O49 | [verl](https://github.com/verl-project/verl) | D；原 volcengine/verl 已迁组织；RL post-training，PPO/GRPO、推训与多 GPU 后端；2026 配套生态扩展 | Apache-2.0；最新 release 未核验 | 训练研究分支；没有算力/奖励质量时不能靠“接入verl”宣称RL能力 |
| O50 | [Agent Lightning](https://github.com/microsoft/agent-lightning) | D；v1.0 2026-08 完整重构，proxy 采真实 harness 交互，trainer/gateway/controller、K8s rollout | MIT；v1.0 路线已核验；未核验最新小版本 | 从部署轨迹到训练的进阶入口；旧版“任意agent零侵入”教程不能直接套当前 API |

## 重要条目的深入取舍（18 个）

下列每一项均在 README 之外交叉检查了 release、迁移说明或官方实现/评测文档。成本档位是对单人项目的判断：低=adapter级工作，中=新增子系统，高=运行环境/数据/训练系统。它们不是价格报价。

| 项目 | 为什么值得深读 | 需要自己补上的边界 / 实验 | 集成成本判断 |
|---|---|---|---|
| LangGraph | [persistence 文档](https://docs.langchain.com/oss/python/langgraph/persistence) 区分 thread checkpointer 与跨 thread store；in-memory saver 不跨进程存活 | 用持久化数据库验证 crash/restart/HITL；外部动作的幂等不能由 checkpoint 名称保证 | 中；可直接做主 runtime |
| Deep Agents | [backend 文档](https://docs.langchain.com/oss/python/deepagents/backends) 区分 thread state、local filesystem、store、sandbox；其 README 明确权限应在 tool/sandbox 层执行 | 建立最小 loop vs 完整 harness 对照；测试 context offload 后证据能否找回，不能只统计少用 token | 中；易有“原生能力被误算自研”问题 |
| MAF | [最新 release notes](https://github.com/microsoft/agent-framework/releases) 仍在细化 MCP approval、compaction、连接所有权和 telemetry；可见运行时问题比角色定义更具体 | 基于当前 Python/.NET 单语言 API 做选型；实验性 provider 与稳定 API 分开 | 中 |
| AutoGen / SK 迁移 | [AutoGen](https://github.com/microsoft/autogen/blob/main/README.md) 与 [SK](https://github.com/microsoft/semantic-kernel) 同指 MAF 后继路线 | 旧框架案例可复现作历史对照，但不能把迁移计划外包给将来的自己 | 不建议新增核心依赖 |
| ADK 2.0 | [release](https://github.com/google/adk-python/releases) 与当前 README 确认 Workflow/Task API，不再只靠旧的 sequential/parallel agent 介绍 | 按具体功能确认 stable/experimental；A2A adapter、恢复和限制次数做行为测试 | 中 |
| Pydantic AI | [当前官方仓库](https://github.com/pydantic/pydantic-ai) 把 harness capabilities、typed graph、trajectory eval 拆成可组合包 | typed schema 保证结构，不保证事实或工具正确；补业务 invariant 与 held-out tests | 中；Python 项目可择其作为轻量 loop |
| AgentScope 2.0 | [Runtime 迁移公告](https://github.com/agentscope-ai/agentscope-runtime) 证实服务/隔离/观测已整合；2.0 有 TeamPipeline 和上下文 middleware | 验证租户 scope、跨 agent memory 访问、被中断工具与回传格式；不要重复部署旧 Runtime | 中；国内模型兼容值得优先试 |
| OpenHands SDK | [Agent Server README](https://github.com/openhands/software-agent-sdk/blob/main/openhands-agent-server/openhands/agent_server/README.md) 定义 conversation/event/WebSocket；typed unions要求兼容未知 variant | fork 出事件驱动任务账本思路，而不是嵌入全部 UI；验证远程 workspace 与任务状态一致性 | 中到高 |
| mini-swe-agent | [官方使用说明](https://github.com/SWE-agent/mini-swe-agent/blob/main/docs/usage/mini.md) 有 confirm/yolo/human 模式和完整 history；[Verified 规则](https://www.swebench.com/verified) 说明 v1/v2 scaffold 差异 | 相同模型、环境、任务和预算下比较，否则 multi-agent提升可能只因更多采样 | 低；强烈推荐必做基线 |
| DeepSeek Harness | [README](https://github.com/deepseek-ai/deepseek-harness) 声明 preview；[release](https://github.com/deepseek-ai/deepseek-harness/releases) 同时存在 rc/alpha 线，插件与subagent机制快速迭代 | 以可替换 adapter 和单独技术实验接入；插件执行权限/升级失败恢复不能交给模型自管 | 中到高；值得读，不无条件押注 |
| DeerFlow 2.1 | [官方 tag](https://github.com/bytedance/deer-flow/releases/tag/v2.1.0) 的 receipt/acceptance criteria、lease-backed batches、并发与预算设计已形成真实工程议题 | 子 Agent 需交付文件/结果句柄和验证证据；parent 独立核验，无法判断标未验证；评估是否降低伪完成率 | 高；优先借鉴局部设计 |
| Letta / Mem0 / Graphiti | [Letta 活跃源码](https://github.com/letta-ai/letta-code) 是 stateful harness；[Mem0](https://github.com/mem0ai/mem0) 是 memory layer；[Graphiti](https://github.com/getzep/graphiti) 是 temporal graph，三者层次不同 | 不全装；先明确 memory 的用户/项目/任务 scope、来源、时效、纠错和遗忘策略，再选择一个 adapter | 中到高 |
| OpenSandbox / Daytona | [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) 可自托管并控制 egress/凭据；[Daytona 公共 core](https://github.com/daytonaio/daytona) 已停更但云路线另存 | 记录 host/container/microVM 边界，做网络拒绝/凭据不可读/跨任务访问拒绝测试；provider故障不能算 agent思考错误 | 高；可先用受控 Docker 做开发基线，再加一种更强隔离后端 |
| SWE-bench Pro V2 | [协议](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md) 要求 agent phase offline、只放模型endpoint，patch 在全新环境评分；gold/nop 双 sanity check | 自建业务任务也做独立 verifier、reference solution、错误/空结果不得过关；执行期与评分期分离 | 高；可选小子集学规范 |
| Terminal-Bench 4 / Harbor | [TB4](https://www.tbench.ai/news/terminal-bench-4-0) 明确资源变化需重跑，verifier变化需重新评分；[Harbor](https://github.com/harbor-framework/harbor) 统一runner与环境 | 固定 task、镜像、agent、model、预算和verifier版本；先跑oracle多次排环境噪声，再评agent | 中到高 |
| τ-bench 2.0 | [release](https://github.com/sierra-research/tau2-bench/releases/tag/v2.0.0) 明确 2.0/1.x 不可比、judges只诊断不改reward；中文 pack 可直接启发双语测试 | 用户模拟器/judge/model/任务集都锁版本；分别报告事务完成、policy遵守、交互质量，避免只看最终话术 | 中；业务Agent评测优先 |
| OTel / Langfuse / Phoenix | [OTel 当前仓库](https://github.com/open-telemetry/semantic-conventions-genai)、[Langfuse许可](https://github.com/langfuse/langfuse)、[Phoenix许可](https://github.com/Arize-ai/phoenix/blob/main/LICENSE) 明确标准与产品边界 | 保留本地结构化事件与export，再任选一个 UI；observability工具不能替代确定性验收 | 低到中；后端只选一个 |
| Agent Lightning v1.0 | [官方 README](https://github.com/microsoft/agent-lightning) 将真实harness保留在训练loop，gateway采轨迹；与旧版架构已不相同 | 先有训练/验证/测试隔离、reward-hack测试、baseline，再做小规模SFT/RL；GPU集群本身不是效果证明 | 高；建议进阶分支 |

## 最新现状核查中发现的“过时陷阱”

1. **AutoGen / Semantic Kernel → Microsoft Agent Framework。** AutoGen README顶部现已明确归档与停止维护；同页下方还遗留maintenance/community-managed表述。以顶部新通知为准，不能把三者同时当活跃同级主框架堆上去。[AutoGen](https://github.com/microsoft/autogen/blob/main/README.md)、[SK](https://github.com/microsoft/semantic-kernel)
2. **AgentScope Runtime → AgentScope 2.0。** 服务与工具隔离已内置，独立 Runtime 仓库有归档告知。[公告](https://github.com/agentscope-ai/agentscope-runtime)
3. **SWE-agent → mini-swe-agent 主开发路线。** “大框架更先进”不是证据；朴素loop必须保留作公平基线。[官方建议](https://github.com/SWE-agent/SWE-agent/blob/main/docs/index.md)
4. **TB4 已发布，TB4.1/5 是路线图；Harbor README 中 TB2 只是示例。** benchmark 与 harness 的文档更新不同步。[TB4](https://www.tbench.ai/news/terminal-bench-4-0)、[Harbor](https://github.com/harbor-framework/harbor)
5. **SWE-bench Pro 当前 default 已是 V2 642任务；731是 V1。** 官方明确保留legacy管线供复现。[V2说明](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md)
6. **tau2-bench 仓库名没有跟版本命名一起变。** 搜索根页缓存曾仍显示τ³/1.0.1；直接打开 main/release已是10月发布的2.0.0。以 release/tag 和具体 manifest 为准。[当前README](https://github.com/sierra-research/tau2-bench/blob/main/README.md)、[release](https://github.com/sierra-research/tau2-bench/releases/tag/v2.0.0)
7. **Daytona 云服务可用性与公共 core 活跃性是两件事。** 公开仓库明确6月起不再收更新，不能凭star数断言适合自托管长期维护。[README](https://github.com/daytonaio/daytona)
8. **Letta 旧 V1 server、Pi 旧组织、OpenSandbox 旧组织、verl 旧组织、OTel旧文档路径均需跟踪。** 选型记录要保存 canonical URL、tag、迁移入口。[Letta](https://github.com/letta-ai/letta)、[Pi](https://github.com/earendil-works/pi)、[OpenSandbox](https://github.com/opensandbox-group/OpenSandbox)、[verl](https://github.com/verl-project/verl)、[OTel](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
9. **平台成绩不等于开源实现成绩。** Mem0 当前README显式说明榜单表含托管平台专有优化；Browser Use也同时有库/CLI/hosted产品。[Mem0](https://github.com/mem0ai/mem0)、[Browser Use](https://github.com/browser-use/browser-use)
10. **“开源”营销词不替代 LICENSE。** Phoenix仓库LICENSE为ELv2；Langfuse/Mastra都有ee范围。这里仅记录许可现状，不据此给法律结论。[Phoenix](https://github.com/Arize-ai/phoenix/blob/main/LICENSE)、[Langfuse](https://github.com/langfuse/langfuse)、[Mastra](https://github.com/mastra-ai/mastra/blob/main/LICENSE.md)

## 收敛 shortlist：按层择一，不做框架博览会

以下是面向“单人可做、能证明工程深度、可随模型演进”的建议，不是通用性能排名。

| 需求 | 优先 shortlist | 原因 / 决策办法 |
|---|---|---|
| 主 runtime | LangGraph / AgentScope 2.0 / MAF / ADK 2.0 四选一 | 用同一批10-20任务试恢复、HITL、并发、traces与国产provider兼容；先选能解释和维护的一种 |
| 强类型轻量 loop | Pydantic AI / OpenAI Agents SDK 二选一 | 不需要复杂图时可替代主runtime；不要为了覆盖JD同时引四个编排框架 |
| harness 基线 / 设计参照 | mini-swe-agent、Deep Agents、DeerFlow 2.1、OpenHands SDK | 分别代表极简loop、开箱harness、可验证多Agent交付、编码workspace/event架构 |
| 新技术实验 | DeepSeek Harness、Pi / OpenCode | 用adapter验证插件/运行时设计；不把preview API深嵌业务域 |
| 文档检索 | 简单BM25+向量+rerank基线；需要复杂格式再选RAGFlow/LlamaIndex部件 | 先测数据质量与检索收益，避免RAG平台吞掉整个项目 |
| 记忆 | 无长期记忆基线 → 文件/数据库可溯源记忆 → Mem0或Graphiti adapter | 只有重复长期任务出现可量化收益才加；Letta作为整体harness对照更合适 |
| 环境 | 受控Docker开发基线 + OpenSandbox或E2B一种后端 | 工程深度来自边界验证、资源回收和故障恢复，不来自接满所有provider |
| 工具接口 | 自有typed tools + MCP adapter；跨服务才A2A | 工具语义、scope、幂等、错误分类比协议数量更关键 |
| 观测 | 自有事件schema + OTel + Langfuse或Phoenix一个后端 | 任务/agent/tool/model/approval/span可关联，数据随时可export |
| 评测 | 业务自建集为主；τ-bench2.0/Harbor为参照；编码方向加SWE-Pro V2或Live子集 | 最终结果、执行轨迹、环境错误、安全与预算分别统计 |
| 优化 | 先prompt/tool/context消融，再DSPy；GPU预算明确后Agent Lightning v1/verl | 没有held-out与奖励设计就不做“自进化”宣传 |

## 建议转化为项目的原创工作

最能体现个人深度的空白不是再写一个所有功能都有的SDK，而是在明确业务任务上构建 **可验证、可恢复、预算可控的执行与评测闭环**。建议形成以下可审阅交付物：

1. 一套任务契约：输入、数据snapshot、允许动作、交付artifact、确定性验收器、预算、权限；检索型任务与会产生状态变更的事务任务均有样本。
2. 一个真实可恢复harness：状态机、任务账本、工具注册、错误分类、timeout/retry/cancel、checkpoint、approval、artifact store、token/cost budget；业务副作用有幂等键和可核验结果。
3. 有触发条件的multi-agent：只将可独立验收、可并行或需要隔离上下文的任务拆给worker；输出是artifact+evidence，parent做独立验收。设计可参考DeerFlow，但实现与实验结果明确标明个人贡献。
4. 统一轨迹：每次model/tool/委托/检索/审批都能关联run与版本，能回答“为什么失败、哪些工具造成代价、恢复是否重复动作”，并导出公开可脱敏数据。
5. 公平对照与消融：同模型同预算下比较单Agent、固定workflow、多Agent；再分别关闭memory、context compaction、verifier、重试与任务路由。报告真实的成功率/成本/时延与置信区间，不预设multi-agent必胜。
6. 单独的失败回归：无效工具参数、403/429、超时、worker崩溃、checkpoint恢复、重复提交、过时知识、工具输出注入、伪造完成报告、verifier可被污染等；每种有明确预期行为。
7. 持续更新制度：锁定模型ID、SDK/tag、镜像digest、任务与verifier版本；新增模型先复跑基线再决定切换。技术组件可换，业务验收与实验方法保留。

这些是根据上述接口与评测设计得出的项目建议，不是声称已实现的功能或已经取得的结果。

## 局限与后续复核

- 这是广度优先的公开资料调研，没有clone全量源码或实测50个项目；深查主要针对维护状态、接口边界、最新版本、评分协议与集成决策。真正实施前对 shortlist 做短时技术验证即可，不应同时安装全部项目。
- 大多数条目没有逐一核验最近commit/release的精确时间，表中已明确。release页面和README可能相互滞后；确定采用时应记录具体tag/commit与依赖锁文件。
- 许可证只核对了可读标签/文本，不构成法务判断；若要二次商业托管，再逐组件核验。评测数据与任务原仓库的许可需要分别检查。
- 本调研避免将厂商self-reported benchmark当独立结果，也避免把公开benchmark分数等同JD全覆盖。实际项目还要与招聘证据表逐能力映射。
