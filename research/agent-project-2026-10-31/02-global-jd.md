# 海外 AI Agent 招聘证据：从 JD 倒推个人项目

调研基准日：2026-10-31（Asia/Shanghai）。本文件是广泛搜集后的招聘侧证据，不是岗位投递清单，也不保证页面仍在招聘。

## 样本、证据分级与检索方法

本轮定位 **13 家公司、32 条具体官方岗位材料：主表30条，Apple补充2条**，另记录 Meta 未取得可用官方 JD。样本有意覆盖应用开发、Agent 平台/harness、评测、安全和模型研究，因此不能用来推算全行业岗位比例。

- **A：官方页面正文实读。** 本轮 17 个样本；Microsoft 两个岗位来自同一官方上海职位列表，正文完整，但未取得独立岗位 ID。
- **B：官方搜索索引证据。** 本轮 15 个样本（含Apple2条）；职责或要求来自官方域名/官方 ATS 的搜索索引，但正文页受动态加载限制、已重定向或返回 404。可证明招聘材料曾出现这些要求，不能证明检索时仍在招。
- 第三方转载仅用于发现线索，没有进入下面的 32 条岗位材料。
- “发布日期”“页面更新时间”“搜索引擎抓取时间”分别处理。没有官方绝对日期的记为“未标明”，不依据抓取时间反推发布日。Workday 的“至少接受申请至某日”也不是发布日期。

先按公司检索，再以 harness / orchestration / evaluation / tool use / MCP / sandbox / memory / agent platform / reinforcement learning 等词横向补漏；随后对具体岗位链接做 open 复核。动态页面不可读时保留 B 级，不用第三方文本补成 A 级。正文中的能力关键词是中文释义，不是完整 JD 引用。

官方站与 ATS 关系的辅助核验：Cognition 的[官方招聘页](https://cognition.com/careers)链接其 Ashby 岗位；Replit 的[官方招聘页](https://replit.com/careers)直接提供可读岗位正文；Cursor 的[官方招聘页](https://cursor.com/careers)提供具体职位链接。Ashby 官方说明其[公开招聘 API](https://developers.ashbyhq.com/docs/public-job-posting-api)可返回发布职位，但本环境请求失败，未据此断言当前发布状态。

## 30 个具体岗位证据

类别：应用=构建 Agent 产品/业务流程；平台=运行时/harness/基础设施；评测=评测与实验系统；研究=模型/后训练/RL/研究环境；安全=权限与执行安全。一个岗位可能跨类。

| ID | 公司、具体岗位与官方来源 | 类别 | 证据与日期 | 可用于项目设计的明确要求（释义） |
|---|---|---|---|---|
| G01 | OpenAI：[Software Engineer, API Agents](https://openai.com/careers/software-engineer-api-agents-san-francisco/) | 平台/应用 | A；发布日未标明 | 共享 harness、搜索与连接上下文、computer use、记忆、委派与多 Agent；长期工作流；隔离执行、身份权限、可观测、评测；任务完成率/成本/延迟。要求 7+ 年专业工程经验，明确偏软件系统工程。 |
| G02 | OpenAI：[Software Engineer, Cloud Agents](https://openai.com/careers/software-engineer-cloud-agents-san-francisco/) | 平台 | A；未标明 | 云端长期 Agent 的编排、sandbox、隔离、存储、连接、秘密与身份、可观测、可靠性及成本；分布式系统。要求 9+ 年专业工程经验。 |
| G03 | OpenAI：[Agent Post-Training, Frontier Evals and Environments Research](https://openai.com/careers/agent-post-training-frontier-evals-and-environments-research-san-francisco/) | 研究/评测 | B；索引可读，open 重定向招聘总页 | 构建有挑战性的 RL 环境、自动行为探索、持续评测；关注测量可靠性、方差与规模化；数据、grader、训练反馈闭环。此条仅作索引/历史证据。 |
| G04 | Anthropic：[Staff+ Software Engineer, Claude Managed Agents](https://job-boards.greenhouse.io/anthropic/jobs/5395767008) | 平台/评测 | A；未标明 | 持久状态、会话、执行环境、凭证、错误恢复；context caching/compaction/memory；每代模型用 eval 重新验证 harness 假设；多 Agent、预算与成功标准、trace、稳定 API。要求至少 8 年后端/分布式/基础设施经验。 |
| G05 | Anthropic：[Applied AI Engineer, Enterprise](https://job-boards.greenhouse.io/anthropic/jobs/5057647008) | 应用 | A；未标明 | 从客户需求到原型、评测套件与部署；prompt、Agent 框架、transcript analysis、MCP、规模化落地；Python/TypeScript。要求 4+ 年技术岗位经历并强调客户沟通。 |
| G06 | Anthropic：[Staff+ Software Engineer, Claude App Infrastructure](https://job-boards.greenhouse.io/anthropic/jobs/5065894008) | 平台/安全 | A；未标明 | sandbox、安全代码执行；长期任务 checkpoint/recovery/resumption；委托认证授权；执行可观测和调试；状态机、durable execution，多租户与容器隔离。 |
| G07 | Anthropic：[Product Engineer, Computer Use](https://job-boards.greenhouse.io/anthropic/jobs/5238637008) | 应用/平台 | A；未标明 | browser/computer use 产品端到端交付；修复 harness 鲁棒性问题并量化成功率；浏览器/桌面自动化、eval、工具集成、guardrails；真实用户反馈。 |
| G08 | Anthropic：[Software Engineer, Staff: Applied AI, Science & Engineering](https://job-boards.greenhouse.io/anthropic/jobs/5444766008) | 应用/评测 | A；未标明 | 文献→假设→模拟→分析→设计迭代的研究循环；接入专业计算工具；把开放问题变成可检验任务与成功标准；复用组件。8+ 年软件经验，领域研究经验为加分项。 |
| G09 | Google DeepMind：[Software Engineer, Applied AI Agents, Professional Intelligence](https://www.google.com/about/careers/applications/jobs/results/74956705875534534) | 应用/评测 | A；未标明 | Python/TS；prompt、tool/function calling、RAG、编排；typed tools/skills/plugins；引用和 grounding 验证、权限感知检索；专家数据集、事实性/引用/多步推理评测；CI/CD、监控。 |
| G10 | Google：[Software Engineer, Agentic Infrastructure for Data Engineering](https://www.google.com/about/careers/applications/jobs/results/79299054445437638-software-engineer-agentic-infrastructure-for-data-engineering) | 平台/安全 | B；索引可读，open 回职位搜索页 | Agent 平台原语、guardrails、知识集成；变更前校验影响、安全与可逆性；编排/工作流、分布式系统、API。不能据此确认仍在招。 |
| G11 | Google：[Software Engineer II, Commerce, Business Agent](https://www.google.com/about/careers/applications/jobs/results/124268043860615878-software-engineer-ii-commerce-business-agent) | 应用 | B；索引可读，open 回职位搜索页 | Early 级别；1 年软件开发/算法及全栈经历；低延迟多轮推理/工具调用；LLM、Agent 架构与 GenAI 自动评测作为加分项。 |
| G12 | Microsoft：[Software Engineer II - Azure SRE Agent（上海官方列表）](https://careers.microsoft.com/v2/global/en/locations/shanghai.html) | 应用/平台/评测 | A；官方显示更新 2026-10-29 | 监测→诊断→缓解事故；工具、规划执行循环、编排、评测、安全；telemetry/实验/用户反馈；可观测、渐进交付、事故后加固。列出 4+ 年编码、3+ 年云/分布式经验偏好。 |
| G13 | Microsoft：[Software Engineer II - Agentic Sandbox（同列表）](https://careers.microsoft.com/v2/global/en/locations/shanghai.html) | 平台/安全 | A；更新 2026-10-29 | 隔离执行、短期/有状态环境、快启动、暂停恢复/快照/持久存储；网络出口策略、身份秘密；控制面/数据面；安全/性能/故障容错测试。基础要求 4+ 年工程经验或同等经历。 |
| G14 | Amazon Ads：[Software Development Engineer, Agent Platforms & Services，10530139](https://www.amazon.jobs/en/jobs/10530139/software-development-engineer-agent-platforms-services) | 平台/应用/评测 | A；发布日未标明 | 多专长子 Agent 编排；scoped 权限/身份；专家反馈信号与 RL 集成；端到端评测、回归检测、质量门禁；并发账户下可靠性/观测/性能。基础要求 3+ 年开发、2+ 年架构经验等。 |
| G15 | AWS：[Software Development Engineer, AWS Agentic AI，10584176](https://www.amazon.jobs/en/jobs/10584176/software-development-engineer-aws-agentic-ai) | 平台 | A；未标明 | AgentCore 控制面 API、执行数据面、部署编排；托管运行、依赖管理、冷启动/调用延迟和资源优化；监控运维。ML 系统经验为偏好，非必要条件；软件/分布式基本功是重点。 |
| G16 | AWS：[Software Development Engineer - AgentCore, AWS Agentic AI，10565536](https://amazon.jobs/en/jobs/10565536/software-development-engineer-agentcore-aws-agentic-ai) | 平台/harness | B；索引可读，open 返回 404 | 以配置定义模型/工具/skills/记忆/限制的 managed loop；session、isolation、identity、network、observability；分布式状态、低延迟 streaming、跨服务 API。只作索引/历史材料。 |
| G17 | NVIDIA：[Senior Software Engineer, Agentic AI，JR2017340](https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Senior-Software-Engineer--Agentic-AI_JR2017340) | 平台/评测 | B；Workday 正文 open 为空；发布日未确认 | 开源库与 harness/framework 优化；benchmark 瓶颈、成本/延迟/质量；异步与事件系统、middleware/plugin/guardrail/policy、profiling、tracing；8+ 年工程经验。索引中的申请接受日期不能作发布日期。 |
| G18 | Salesforce：[Machine Learning Platform Engineer，JR341270](https://careers.salesforce.com/en/jobs/jr341270/machine-learning-platform-engineer/) | 平台/应用/安全 | B；官方索引；open 转新域后空正文；索引显示 2026-06-12 | 真实工程 Agent、MCP 工具/技能市场、权限/secrets、CI/CD、可审计 trace/sandbox；平台、harness、eval、可观测的整体设计；memory/RAG 为加分项。9+ 年平台/软件/ML 基础设施经验。 |
| G19 | Databricks：[Sr Software Engineer - Agentic Applications (Full Stack)，8679982002](https://www.databricks.com/company/careers/integration-data-engineering-and-applications/sr-software-engineer---agentic-applications-full-stack-8679982002) | 应用 | A；未标明 | 至少一个生产部署的 Agent/LLM 应用；Python/React，LangChain/LangGraph/ReAct，工具和 API 集成；运行观测/log/trace；大型企业应用和系统设计。5+ 年全栈经验。 |
| G20 | Cursor：[Software Engineer, Bugbot](https://cursor.com/careers/software-engineer-bugbot) | 应用/评测 | A；未标明 | PR/CI 工作流集成；prompt/model routing/context selection/orchestration；precision/recall 与误报、eval 数据、可靠性、成本延迟；全栈交付与外部用户反馈。 |
| G21 | Cursor 官方站：[Software Engineer, RL Environments](https://cursor.com/careers/software-engineer-rl-environments) | 研究环境/平台 | A；未标明；正文组织称 SpaceXAI，应复核团队归属 | 把真实/供应商/合成数据转成逼真、多样、端到端 RL 任务环境；自动质量检查、共享平台与自助 API；与研究合作把能力目标变成实验。此条按官网宿主列出，不额外推断公司组织变化。 |
| G22 | Cognition：[Software Engineer, Infrastructure](https://jobs.ashbyhq.com/cognition/13fdacf7-b4dc-4b9a-ac43-addc87de79ec) | 平台 | B；官方站仍有岗位链接；Ashby open 为 JS 壳 | 长程任务、subagent、工具；VM sandbox、容器、资源调度/隔离、网络和平台；规模化会话、低延迟、Python 和系统工程。 |
| G23 | Cognition：[Research Engineer, Infrastructure](https://jobs.ashbyhq.com/cognition/b6f96827-ce14-44f4-98fa-b1b8640858b6/) | 研究基础设施 | B；官方索引可读；职位标题后续可能调整 | 大规模 Agent rollout/VM sandbox；分布式训练/实验/数据管线；checkpoint/fault tolerance；PyTorch、Python/C++、GPU profiling 与多维并行。个人 API 项目无法替代此类训练系统经历。 |
| G24 | Cognition：[Research Engineer, Safety & Alignment](https://jobs.ashbyhq.com/cognition/023cea7e-70db-4f79-8e82-c57564466622) | 安全/研究/评测 | B；官方站有岗位链接，正文取自官方索引 | 实际 Agent 循环中的评测/red teaming/权限与升级；tool misuse、规格投机、长期漂移、对抗输入；实验统计、Python+PyTorch/JAX；研究经历或同等能力。 |
| G25 | Replit：[Staff Software Engineer, Agent Platform](https://replit.com/careers/jobs/43bd4e63-22c3-4b80-abd2-67eaf2c89790) | 平台/应用 | A；未标明 | Agent 与内部系统/外部 MCP 的稳定接口；产品工程工具与前后端平台；系统/DX/产品结合；8+ 年服务/平台经验；event sourcing、协作编辑为加分项。 |
| G26 | Replit：[AI Agent Security Architect](https://replit.com/careers/jobs/df7b6d30-9da1-4ace-8121-17c2aa55aa6f) | 安全/平台 | A；未标明 | 间接 prompt injection、goal hijacking、工具参数篡改；MCP、多 Agent 安全；短命隔离执行、最小权限/委派/HITL；memory/RAG 多租户隔离、可审计日志。6+ 年安全且 2+ 年 AI/ML 安全。 |
| G27 | Replit：[Staff Software Engineer, Agentic Ads](https://jobs.ashbyhq.com/replit/4df82fb0-0bcb-4034-89ce-09e679b00fe7) | 应用/平台/评测 | B；官方 ATS 索引，open 为 JS 壳；未标明 | 有状态跨平台动作；幂等、重试、对账、部分失败恢复、过期凭证与限流；显式授权/预算/暂停；计划/工具/策略/花费安全的 eval；量化增量业务结果。 |
| G28 | Perplexity：[MTS, AI Software Engineer, Agent Engine](https://jobs.ashbyhq.com/perplexity/d865c821-9a27-416c-9c6a-14132a86f760) | 应用/平台 | B；官方 ATS 索引，open 为 JS 壳；未标明 | harness、skills/plugin、模型训练/RL、浏览器技术是可深入的方向；本地/云端/不同执行器的抽象；多模态状态、权限架构；Python 为基础。 |
| G29 | Perplexity：[MTS, Software Engineer, Enterprise Agent Evals & Efficiency](https://jobs.ashbyhq.com/Perplexity/f3814af2-55a3-49a5-b0cb-67199a2a45fb) | 评测/应用/平台 | B；官方 ATS 索引，open 为 JS 壳；未标明 | 可复现跨系统/用户角色/权限/状态环境；人类校准 grader；轨迹与生产失败→harness/tool/skill 改进；模型/effort routing、context/cache；回归门禁；每成功任务成本。5+ 年工程经历。 |
| G30 | Perplexity：[MTS, Machine Learning Engineer, Search Agent RL](https://jobs.ashbyhq.com/perplexity/9cec9b33-06f2-4ba1-8c9e-20a598361ca2) | 研究/应用 | B；官方索引；未逐页取得正文 | 训练和评测多 Agent 协调；长链工具/context/execution harness；检索排序与搜索界面；数据/reward/eval；训练到部署实验、质量/延迟/成本。 |

## 补充的 Apple 样本：应纳入项目可行性判断，但单列避免误导正文验证数

Apple 不包含在上面的 12 家/30 岗统计内，以下两岗均为 **B：官方索引正文可读，open 动态页面不足以复核全文**。因此，整个海外资料包实际触达 **13 家公司、32 个官方岗位材料**，其中 A 仍为 17 条，B 为 15 条。

| ID | 官方来源 | 日期、要求及对项目的启示 |
|---|---|---|
| G31 | Apple：[Applied AI Engineer, Agent Harness，200688056-0836](https://jobs.apple.com/en-ua/details/200688056-0836/applied-ai-engineer-agent-harness?team=SFTWR) | 官方索引显示发布 2026-10-08。Agent loop、工具执行、context、多步中断恢复；device/server streaming；安全隐私；eval/latency、tracing/replay/debug。基础要求 2+ 年行业经验、系统语言、并发/IPC；明确认可专业工作或 **“substantial personal projects”** 中的 LLM 实践。这是“个人项目确实可证明某些岗位能力”的直接证据。 |
| G32 | Apple：[AI Evaluations Engineer, US Decision Intelligence，200684460-0836](https://jobs.apple.com/de-at/details/200684460-0836/ai-evaluations-engineer-us-decision-intelligence?team=MLAI) | 官方索引显示发布 2026-09-18。端到端 AI/Agent 评测管线；trajectory、end-to-end、component 多层评测，tool-call correctness；要求 5+ 年相关数据/AI/软件/QA 经历。 |

## JD 共性矩阵：哪些能力要有真实项目证据

“出现”仅表示样本显式提及，不代表未列出的公司没有需求。这里不按关键词次数排名：岗位重复、资深级别偏多、动态索引及取样方式都可能扭曲频次。

| 能力 | 强证据样本 | 个人项目应该交付的可检验证据（研究者建议，非 JD 原文） |
|---|---|---|
| 工具协议与 API 集成 | G01/G05/G09/G14/G19/G25 | Typed schema、参数校验、超时/限流/取消、工具结果验证；一个 MCP server 和实际客户端；隔离的读/写权限；工具失败用例。 |
| 长期任务与 durable execution | G01/G02/G04/G06/G12/G13；B: G27/G31 | 可持久化任务状态、checkpoint、进程崩溃后恢复；明确幂等键、重复投递、部分失败的处理；中断恢复演示。 |
| 多 Agent/委派 | G01/G04/G14；B: G22/G30 | 有适用条件的 supervisor-worker 或专家并行；typed handoff/shared artifact；取消与预算传播；与单 Agent 基线作消融。 |
| Context engineering 与记忆 | G01/G04/G09；B: G18/G29/G31 | 上下文组装与压缩、检索预算；记忆来源/写入策略/TTL/冲突/权限；长任务和跨会话的独立评测。 |
| 评测、grader、回归门禁 | G01/G04/G05/G07/G09/G14/G20；B: G29/G32 | 版本化任务集；真实状态/执行结果 grader；组件与轨迹诊断；LLM judge 对人类校准；统计方差/重复运行；CI 回归门禁。 |
| 可观测与调试 | G01/G02/G06/G12/G13/G14/G15/G19/G20 | trace、工具事件、模型/版本/token/成本/延迟；失败分类；可重放工具观测；配置与数据版本。注意回放不等于保证重现模型采样。 |
| 安全执行、权限与人类控制 | G01/G02/G06/G13/G14/G26；B: G27 | 最小权限/任务凭证、sandbox、网络出口限制；恶意文档/间接注入测试；审批和暂停边界；审计。容器本身不能被宣称等于充分的敌对代码隔离。 |
| 性能/成本与模型路由 | G01/G02/G04/G15/G20；B: G17/G29 | 成功率—延迟—每成功任务成本曲线；模型/effort/router 对照；缓存与并发调度消融；失败耗费单独列出。 |
| 搜索/RAG/证据性 | G01/G09；B: G18/G30 | 混合检索/重排的实际需求；权限过滤；事实与引用追溯；冲突来源与时间戳；不要只展示“能够检索”的 demo。 |
| 工程与真实用户结果 | G05/G07/G08/G09/G12/G19/G20/G25 | 一个具体业务流程从用户目标到可验收动作/产物；部署、测试、可用界面、用户反馈和改进记录；故障与成本报告。 |
| 后训练/RL/模型研究 | B: G03/G23/G24/G30；G21 的环境工程为 A | 可选拓展：高质量 rollout 数据、明确 reward、可复现小模型实验、held-out 环境。纯调用 API 的项目不可称已经覆盖大规模训练/分布式并行。 |

## 从招聘信息得到的筛选结论

1. **优先围绕“一个可验证业务工作流 + 可更换模型的 harness + 评测闭环”设计项目。** OpenAI API Agents 把任务完成率、成本和延迟列为共同目标；Anthropic Managed Agents 直接强调 API 契约可保持稳定，而底层模型和 harness 假设应随模型更新通过 eval 重验。由此推断，持久竞争力来自可度量和可演进的系统边界，而不是固定使用某个框架版本。[G01 官方 JD](https://openai.com/careers/software-engineer-api-agents-san-francisco/)、[G04 官方 JD](https://job-boards.greenhouse.io/anthropic/jobs/5395767008)

2. **多 Agent 是要实验验证的结构选项。** JD 对委派和多专长协调确有需求，但这些材料没有证明任意任务都应采用多 Agent。个人项目最有说服力的证据是：在相同模型、预算和任务集上，明确哪些任务从并行/隔离中获益，哪些任务因通信和共享状态而变差。[G14 官方 JD](https://www.amazon.jobs/en/jobs/10530139/software-development-engineer-agent-platforms-services)

3. **“研究报告生成器”本身难以展示所有高价值能力。** Google 的专业 Agent 岗要求引用可信与权限检索，值得保留；Replit 与 Microsoft 又要求真实动作的授权、执行状态、安全和恢复。推断最有覆盖面的流程应有“读取信息→计划→调用工具/生成并执行受控产物→验证→迭代”，并配备可控测试环境。[G09 官方 JD](https://www.google.com/about/careers/applications/jobs/results/74956705875534534)、[G12/G13 官方列表](https://careers.microsoft.com/v2/global/en/locations/shanghai.html)、[G26 官方 JD](https://replit.com/careers/jobs/df7b6d30-9da1-4ace-8121-17c2aa55aa6f)

4. **应用/平台和模型研究应分成主线与可选分支。** AWS 平台岗明确 ML 经验有帮助但不必需；Cognition 研究基础设施材料却要求大规模 GPU/训练并行与 rollout 系统。这是不同职系，个人项目不能通过堆叠 Agent 名称就同时证明全部资历。[G15 官方 JD](https://www.amazon.jobs/en/jobs/10584176/software-development-engineer-aws-agentic-ai)、[G23 官方索引来源](https://jobs.ashbyhq.com/cognition/b6f96827-ce14-44f4-98fa-b1b8640858b6/)

5. **演示应同时提供质量、恢复、安全和成本证据。** Cursor 的 Bugbot 岗把 precision/recall、误报和信任直接连接到产品质量；Anthropic App Infrastructure 把恢复和授权放到核心职责。推断项目演示应包含成功任务，也包含超时、注入、重复动作、权限不足和状态恢复；只展示顺利路径证据很弱。[G20 官方 JD](https://cursor.com/careers/software-engineer-bugbot)、[G06 官方 JD](https://job-boards.greenhouse.io/anthropic/jobs/5065894008)

## 项目能证明什么，不能替代什么

能证明的部分：Agent loop/工具/状态/上下文/协作的设计能力；如何定义任务成功；如何诊断失败并建立回归；安全和成本边界；可读代码、部署和真实用户迭代；对新模型/框架的比较判断。

不能自动替代的部分：JD 中的 2/4/7/9 年工作年限；高并发生产 on-call 责任；大规模 GPU 分布式训练；安全架构行业经验；领域专家资历、论文及研究贡献；地域/工作资格要求。不要把“技术点演示覆盖”写成“已满足所有公司所有岗位要求”。

建议把最终作品集拆成同一项目的三种入口，而非另起三套系统：应用入口展示用户目标与结果；平台入口展示 harness、恢复/权限/观测；研究入口展示基线、消融、失败分析和可选小规模后训练。这是基于样本的设计建议，不是招聘方统一规定。

## 覆盖缺口与失效记录

- Meta：使用 metacareers.com / metacareers.com/jobs 与 agentic、agents、LLM evaluation 等组合检索，未取得可核验的具体官方 Agent JD；没有用第三方招聘转载补位。不能据此推断 Meta 没有 Agent 岗位。
- Apple：国际区官方搜索索引提供较完整材料，但实际 open 仅有动态壳或访问失败，严格列 B；G31 的绝对日期来自官方索引，而非第三方“posted X days ago”。
- Ashby：Cognition、Perplexity、部分 Replit 岗位 open 只返回 JS 壳。Cognition 部分职位可由官网当前链接确认标题入口，正文仍只能记 B。
- Workday/Salesforce：正文空壳/域名迁移使状态不明；不把索引“刚抓取”解释成刚发布。
- G03、G10、G11、G16：重定向或404明确降低时效可信度；只用于识别曾公开的技能要求。
- 资深岗位偏多，不能把所有 Staff+/Senior 要求当作应届的入门门槛；G11、G31 提供较早职业阶段的参照，但本轮并非校招专门抽样。
- 本轮没有收集薪资用于项目选型，也没有以职位数、公司名气或框架名出现次数推算技术优劣。
