# 国内 Agent 招聘证据：先广泛检索，再区分岗位与项目边界

研究日期：2026-10-31（Asia/Shanghai）。本文件只记录公开招聘要求与据此作出的项目推断，不参与申请、不登录招聘账户。

## 口径与可信度

- 检索覆盖 19 家公司：腾讯、美团、百度、小米、小红书、京东、阿里巴巴、哔哩哔哩、拼多多，以及字节跳动、蚂蚁、快手、网易、携程、华为、智谱、月之暗面、DeepSeek、MiniMax。
- 主表收录 **28 条能从企业官方域名的正文或搜索索引核对职责的岗位，来自 9 家公司**。其中 A 级 9 条，B 级 19 条。另列 1 条明确已下架的历史样本。入口页、只有标题的岗位、第三方转载不进入主表或能力分母。
- **A：官方正文已读。** 用网页工具打开公司招聘详情 URL，获得可读职责。
- **B：官方搜索快照。** 搜索结果指向公司官方招聘详情 URL，并显示职责/要求；直接打开为空、报错或只能看到网页壳。其内容有一手归属，但可能滞后、不完整，不能当作实时招聘状态证明。
- **T：官方标题/入口。** 只能确认岗位标题、招聘入口或项目，不能确认具体技术要求。
- **C：第三方线索。** 聚合站、学校转载、公开数据集等只用于发现官方地址；未从官方内容核对的技术要求不混入主结论。
- 表中日期仅保留官方页面/官方搜索快照明确显示的发布、更新日期；“未显示”不等于近期发布。搜索引擎抓取时间和聚合站收录时间均不作为发布日期。公开可见不等于仍可申请。
- 本研究有意搜索 Agent、Harness 等词，属于目的抽样，且同公司/团队有相关岗位，不能由出现次数推导市场占比、公司投入或求职成功率。

## 28 条官方岗位证据

以下为释义，不是大段原文转载。必需与优先项按能读到的信息区分；缺失要求不补写。

| ID | 公司、岗位与官方来源 | 招聘类型/门槛 | 页面日期 | 级别 | 可核验职责与要求的摘要 |
|---|---|---|---|---|---|
| CN01 | 腾讯：[金融科技-Agent架构设计与推理性能优化工程师](https://careers.tencent.com/jobdesc.html?postId=2092447906002022400) | 社招，5 年以上；本科及以上 | 更新 2026-09-15 | B | Harness、工具/沙箱/Agent 互调；以工具指标和轨迹衡量效率效果；上下文与 Skill 设计；还要求推理框架优化，vLLM/SGLang，卡适配和集群调度为优先。 |
| CN02 | 腾讯：[WorkBuddy-后台开发工程师（生态资产数据方向）](https://careers.tencent.com/jobdesc.html?postId=2101890746188738560) | 社招，5 年以上 | 更新 2026-09-23 | B | Skill/Expert/Connector 资产理解、评估、分发；离在线质量度量与归因；研究开源 MCP/Agent/Skill。Agent 开发、OLAP 与海量 trace/日志经验列为加分。 |
| CN03 | 腾讯：[星星海实验室-AI Infra CPU研发工程师](https://careers.tencent.com/jobdesc.html?postId=2100123159490637824) | 社招，5 年以上；专业性能工程岗 | 更新 2026-09-16 | B | Agent/RL/工具任务的端到端工作负载、性能 benchmark；定位 CPU、缓存、NUMA、I/O、并发和隔离瓶颈；理解代码执行、多 Agent、恢复与长任务。不能用普通 API Agent 项目声称覆盖 CPU 专业能力。 |
| CN04 | 美团：[Agent可靠性技术专家](https://zhaopin.meituan.com/web/position/detail?jobUnionId=4831038591) | 社招，页面经验 3 年；要求主导过生产 Harness | 更新 2026-10-09 | B | 企业人机协作工作流、架构设计、运行稳定性与安全；真实任务/生产问题驱动可靠性评测与优化。复杂分析、策略、创作、多 Agent 的生产经验为优先。 |
| CN05 | 美团：[AI Agent安全Harness相关研发岗（详情未展示标题）](https://zhaopin.meituan.com/web/position/detail?highlightType=social&jobUnionId=4791236953) | 社招；复杂平台/基础设施研发经验 | 未显示 | B | 安全控制覆盖输入输出、Skill/MCP/CLI、命令和资源访问；执行拦截、权限、审计、恢复；防注入、越权、泄露和工具滥用；通过攻击样本验证防护，并控制误拦截与性能影响。 |
| CN06 | 美团：[本地生活AI搜索算法相关岗（详情未展示标题）](https://zhaopin.meituan.com/web/position/detail?highlightType=social&jobUnionId=4761247735) | 社招，硕士及以上，3 年以上搜索/推荐/NLP | 未显示 | B | RAG 搜索 Agent、多轮工具推理；Harness 离线评测、在线流量模拟、多轮自动测试、归因和对抗验证；多源数据、SFT/RLHF、推理成本与性能。 |
| CN07 | 美团：[北斗-大模型算法工程师 SFT/RL/Agent方向](https://zhaopin.meituan.com/web/position/detail?highlightType=campus&jobShareType=1&jobUnionId=4683995941) | 应届北斗计划；算法与研究方向 | 未显示 | B | 预算约束的营销序贯决策；规划、工具链、候选策略、实验和归因；长任务、幂等、可解释性与安全；另有 SFT/DPO/GRPO/PPO/RLVR、AutoResearch、仿真评测与训练推理平台。 |
| CN08 | 百度：[上海-Agent Harness研发工程师 J100779](https://talent.baidu.com/jobs/detail/GRADUATE/74d83772-1bd0-42b9-8cc5-69eb45696b62) | 校招，本科及以上；论文/开源/竞赛为加分 | 页面日期 2026-07-21 | A | 状态、沙箱、反馈、执行约束、上下文交接和 compaction；模型与 Harness 联合优化、人机反馈；要求理解 ReAct/Plan-and-Execute，能分析文件操作和长任务中的框架不足。 |
| CN09 | 百度：[AI Agent开发工程师（实习生）J106681](https://talent.baidu.com/jobs/detail/INTERN/162291c8-43e8-4cc0-9c96-3fb0a7ebb720) | 日常实习；Python 为主、TypeScript 加分 | 页面日期 2026-10-19 | A | 伐谋 Harness、上下文/记忆、多 Agent 与状态流转；Skills 输入输出契约；eval harness、任务集、回归、badcase；优化 token/延迟、缓存并行和收敛；要求从 trace 与日志解释失败和成本。 |
| CN10 | 百度：[云原生Agent Infra高级研发工程师 J100117](https://talent.baidu.com/jobs/detail/SOCIAL/4b326f6b-2c39-461c-ae64-69b4201c680e) | 社招，本科及以上；云原生、分布式基础 | 页面日期 2026-07-21 | A | 沙箱、网关、观测、弹性、多租户隔离、资源/网络控制；大规模多 Agent 编排恢复；CLI/MCP/SDK/Skill；理解 Docker/Kubernetes/Operator；虚拟化、Agentic RL、Serverless、OpenTelemetry 实践为加分。 |
| CN11 | 百度：[Dumate-Agent后端研发 J106087](https://talent.baidu.com/jobs/detail/SOCIAL/86c68ee0-49b2-4f96-9961-bc005139eaf8) | 社招，本科及以上，3 年以上后端 | 页面日期 2026-09-20 | A | 记忆、技能/MCP、组织权限；异步消息、状态持久化、限流重试；凭证、入出站授权、加密；追踪与效果指标；Go/Python、容器、自托管、Redis/PostgreSQL/Kafka。 |
| CN12 | 百度：[伐谋-Agent研发工程师 J99560](https://talent.baidu.com/jobs/detail/SOCIAL/75d3af47-7f79-4d71-862b-6fbca577bb19) | 社招，本科及以上；Go/Python | 页面日期 2026-07-21 | A | 长程规划、工具、代码执行和状态；任务采样、训练调度、结果回传、实验管理；代码自动评估环境；多租户、编排、资源和权限；从原型推进生产可用。 |
| CN13 | 百度：[Agent后端研发工程师 J103882](https://talent.baidu.com/jobs/detail/SOCIAL/d1876313-6604-4e8d-bbcc-0dca5be4e51b) | 社招；Go；Harness云服务经验优先 | 页面日期 2026-07-29 | A | DuMate 云基建、推理链路、网关、数据闭环、Harness/Infra；覆盖设计、研发、集成测试、部署与运维。 |
| CN14 | 小米：[Agent Harness研发工程师](https://xiaomi.jobs.f.mioffice.cn/campus/position/7671284471720020243/detail) | 2027 校招；Python/TypeScript/Go 至少一门；个人/课程项目为加分 | 未显示 | B | 自研 Loop、工具、上下文、记忆与状态；零售/客服/研发/供应链/办公落地；模型+Harness 联合优化；MCP/A2A/Multi-Agent/Sub-agent；要求模型原理、KV Cache、深度使用 Agent 产品。 |
| CN15 | 小米：[大模型agent算法工程师](https://xiaomi.jobs.f.mioffice.cn/campus/position/7670924118350465321/detail?spread=J7NS6YR) | 2027 校招；硕士或博士；JD 要求相关一作顶会论文 | 未显示 | B | 端云、多模态、跨 Agent 共享记忆；自适应读写压缩与持续学习；搜索/反思/进化策略；基于 trace 在线诊断与 Harness 优化。属于研究岗，不能仅靠调用 API 的项目等价覆盖。 |
| CN16 | 小红书：[2027校招-Agent Harness工程师-企业智能](https://job.xiaohongshu.com/campus/position/22074) | 校招，本科及以上；任一主流后端语言；系统工程能力 | 未显示 | B | Runtime 会话/任务/工具/持久化；Serverless 生命周期与弹性；Trace/Log/Metric/Event、回放诊断；身份与最小授权；多 Agent 消息分发、SuperAgent 路由；框架研究改造。 |
| CN17 | 小红书：[2027校招-Agent平台全栈研发工程师](https://job.xiaohongshu.com/campus/position/22059) | 校招；已读职责，完整门槛未核对 | 未显示 | B | 云原生高可用微服务；训练至部署的 LLMOps/DevOps、监控诊断评估；Agent Workflow、Tool/Function Calling、MCP、RAG、Memory、调试和发布。 |
| CN18 | 小红书：[2027校招-Agent应用算法工程师-创新业务](https://job.xiaohongshu.com/campus/position/22486) | 校招，本科及以上；Python/PyTorch/Transformers；论文为加分 | 未显示 | B | Context/Planning/Tool/RAG/Memory；自动 Eval、轨迹分析、LLM-as-Judge；探索合成数据、SFT/RL、轨迹学习；论文复现、原型和真实产品实验。 |
| CN19 | 小红书：[2027校招-智能客服算法工程师（LLM Agent）](https://job.xiaohongshu.com/campus/position/21002) | 校招，本科及以上；要求训练全链路实践；论文/benchmark 成绩优先 | 未显示 | B | 状态跟踪、工具、检索重排；ReAct/Plan-and-Execute/多 Agent；SFT、蒸馏与 RL；Rubric/Judge、AB、数据清洗；推理加速、reward 与 Agentic RL。 |
| CN20 | 小红书：[2027校招-产品工程师（Agent开发）-智能客服](https://job.xiaohongshu.com/campus/position/22481) | 校招，本科及以上或扎实基础实践；真实项目贡献 | 未显示 | B | 客服、退款争议与多方调解；多 Agent、知识检索、工具、规划、权限、评估追踪；完整交付与复盘。要求能解释方案取舍、验证方式、个人贡献，个人项目与开源是加分。 |
| CN21 | 小红书：[AI Agent全栈工程师（采购方向）](https://job.xiaohongshu.com/social/position/21635) | 社招，3 年以上全栈；实际 Agent/个人/黑客松/开源项目 | 未显示 | B | 深入采购真实流程，发现问题、设计开发 Agent，构建知识库和数据集，迭代并对业务结果负责；需求拆解、策略、招投标、议价、合同和交付是业务范围。 |
| CN22 | 小红书：[PE/Agent全栈工程师-大商业&AI](https://job.xiaohongshu.com/social/position/18753) | 社招，本科及以上，至少 2 年开发；实际 Agent/多 Agent 项目 | 未显示 | B | 电商助手、内容导购、评价与撮合；RAG、Planning、SFT、训练、稳定性/SLA、多模态落地；用数据分析指导技术与产品迭代。 |
| CN23 | 京东：[Agent架构开发 220462](https://zhaopin.jd.com/web/job-info-detail?requementId=220462) | 社招，4 年以上；至少一个从0到1落地项目 | 发布 2026-07-09 | A | Agent注册、调度、上下文和工具市场；Harness流式、中断恢复、并发与追踪；短长记忆/RAG；安全检测研判 Agent；多 Agent 经验；安全对抗背景为加分。 |
| CN24 | 京东：[Agent软件工程师 219685](https://zhaopin.jd.com/web/job-info-detail?requementId=219685) | 社招，本科及以上，3 年以上后端/AI应用 | 发布 2026-06-24 | A | 医疗场景编排、工具和状态；SSE/WebSocket/MCP、异步并发、中断重连；RAG重排、压缩和记忆；任务与工具指标、输出安全与压测。此岗把 Harness Engineering 明确用于评测方法。 |
| CN25 | 京东：[软件开发工程师-投放平台部 226656](https://zhaopin.jd.com/web/job-info-detail?requementId=226656) | 社招；要求完整上线、平台基础服务和故障定位经验 | 发布 2026-10-15 | A | 广告/Data/Dev Agent；平台 MCP管理、A2A、Prompt动态配置、插件和安全；多智能体故障与性能分析；端到端业务效率与效果。 |
| CN26 | 阿里巴巴：[算法工程师-AI Agent 199903260012](https://campus-talent.alibaba.com/campus/position/199903260012) | 官方标 Alibaba 2027 Intern；本科及以上；Python及C/C++/Java；框架/论文/开源为加分 | 更新 2026-03-22 | B | Planning/Tool/Memory/RAG；RL、模仿、SFT、DPO/PPO；高可用框架/Runtime、多 Agent与自我迭代；端到端评测、搜索办公创作等场景。业务组跨淘天、国际、云等，不把一个通用岗拆成多公司。 |
| CN27 | 哔哩哔哩：[大语言模型算法实习生 29836](https://jobs.bilibili.com/campus/positions/29836?type=0) | 实习，2027及以后在校生；要求 CPT/SFT/RL 任一相关经验；Agent RL/Harness 为加分 | 发布 2026-08-06 | B | MoE持续预训练、RLVR/RLAIF数据与reward、翻译；长程Agentic RL环境、任务流、轨迹和策略优化；评测脚本。不同方向不等于要求所有候选人同时精通。 |
| CN28 | 拼多多：[2027校招-大模型算法工程师](https://careers.pddglobalhr.com/campus/grad/detail?t=Yy4snT3eIX) | 校招，2026.9—2027.8硕士/博士；训练全流程熟悉为优先 | 页面日期 2026-09-02 | B | 多语言多模态基座、Pretrain/SFT/RL；Long Context、Agent-RL、训推效率；搜索推荐、导购运营客服和代码助手；用AB实验验证用户商家体验与商业收益。 |

## 历史样本与未升级的线索

### 明确下架的历史样本（不计入28条）

[B站推荐算法实习生 28355](https://jobs.bilibili.com/campus/positions/28355)：官方搜索快照显示 2026-07-01 发布，网申截至 2026-08-31，并明确“职位已下架”。职责涉及用 LLM/Agent 将非结构化社区内容转为推荐信号，优先考虑 RAG、多 Agent、工具和自动评测经验。它证明曾有此类岗位，不能据此宣称当前在招。

### 其余10家：入口、标题、转载与读取限制

| 公司 | 实际访问的一手入口/候选官方详情 | 能确认什么 | 未核验内容与后续入口 |
|---|---|---|---|
| 字节跳动 | [Seed官方招聘](https://seed.bytedance.com/zh/career)、[Seed早期人才项目](https://seed.bytedance.com/zh/seedearlycareer) | T：官方列出Code Agent、通用Agent、强化学习、多模态Agent等方向；有2027应届与实习说明 | 详情页大量为空或不可访问。第三方发现的[AI Agent服务端 7325339483112638771](https://jobs.bytedance.com/experienced/position/7325339483112638771/detail)、[豆包策略 7615884905150499077](https://jobs.bytedance.com/experienced/position/7615884905150499077/detail)、[Seed研究 7628902314323806469](https://jobs.bytedance.com/experienced/position/7628902314323806469/detail)、[Harness 7651517511770818869](https://jobs.bytedance.com/experienced/position/7651517511770818869/detail)、[TikTok实习 7701678464139036981](https://jobs.bytedance.com/campus/position/7701678464139036981/detail)均未从官方正文确认技术要求。 |
| 蚂蚁集团 | [官方社招候选详情](https://talent.antgroup.com/off-campus-position?positionId=261030012663790)、[记忆RAG研究实习候选详情](https://talent.antgroup.com/campus-position?positionId=261030012649714) | 官方域名页面可打开但无可读正文 | C：从[前端Agent聚合页](https://jobs.ultraai.site/jobs/ant/261030012663790)和[记忆研究聚合页](https://jobs.ultraai.site/jobs/ant_campus/261030012649714)追到官网；不把转载的长短期记忆、共享一致性、记忆贡献度等要求当作已核实官方JD。 |
| 快手 | [官方社招入口](https://zhaopin.kuaishou.cn/recruit/e/)、[官方校招入口](https://campus.kuaishou.cn/recruit/campus/e/) | T：招聘入口存在；网页工具仅返回启用JavaScript提示 | C：发现[Agent算法32618](https://jobs.ultraai.site/jobs/kuaishou/32618)、[全栈校招13836](https://jobs.ultraai.site/jobs/kuaishou_campus/campus:13836)、[Agent实习25662](https://jobs.ultraai.site/jobs/kuaishou_trainee/25662)，未从官网核对职责。聚合站官网按钮退回首页，也不足以证明该详情当前有效。 |
| 网易 | [候选官方详情58561](https://hr.163.com/job-detail.html?id=58561) | 官方详情抓取报错 | C：[第三方资深Agent开发工程师](https://jobs.ultraai.site/jobs/netease/58561)显示上下文、多Agent、Skill/Workflow等内容；本轮未获一手职责，不计入矩阵。 |
| 携程 | [官方招聘](https://job.ctrip.com/) | T：官方入口；只返回JavaScript提示 | C：[MJ037606测评链路实习线索](https://jobs.ultraai.site/jobs/ctrip/66b816d4-1bca-4405-99c3-a2237ec35619)。转载标题称实习、聚合分类称社招，有字段冲突；不沿用其分类或相对发布时间。 |
| 月之暗面 | [Moka官方租户候选入口](https://app.mokahr.com/social-recruitment/moonshot/148506) | 访问时重定向循环，未读到岗位正文 | C：第三方提到资深Agent、multi-agent产品工程师、AI基础设施等；不继承第三方“官方全文”的标签。 |
| DeepSeek | [官方人才页](https://talent.deepseek.com/)，由[DeepSeek官网](https://www.deepseek.com/)“加入我们”可交叉确认 | T：官方搜索索引可确认 Agent Harness 团队、Agent弹性计算、Agent数据策略等标题；直接打开正文为空 | 不使用 deepseek.ai、deepseek.club 等非该公司官方域名作为招聘一手证据；未从官方详情核实的具体职责不入主表。 |
| MiniMax | [官方 Careers](https://www.minimax.io/careers)→[官方指向的飞书招聘租户](https://vrfi1sk8a0.jobs.feishu.cn/index/) | T：2027校招、2028实习、社招与Top Talent入口；飞书页面无可读岗位正文 | 不拿同名消防企业 minimax.com 的招聘页混入AI公司。未确认具体Agent JD。 |
| 智谱/Z.ai | [官方加入我们](https://www.zhipuai.cn/zh/joinus) | T：校招/社招类别、研发方向；页面提到训练框架等一般方向 | 本轮未定位能核验正文的Agent专岗，不据产品存在推断招聘要求。 |
| 华为 | [官方招聘](https://career.huawei.com/cn)、[部门列表](https://career.huawei.com/cn/department-list)、[挑战课题](https://career.huawei.com/cn/young-genius) | T：云部门公开提及Agent平台，挑战页出现AI Agent多模态智能通信等课题 | 课题/部门简介不等于岗位JD。未纳入普通互联网Agent工程要求统计；不把具身/通信研究当作通用软件项目必须覆盖。 |

### 信息发现渠道与方法限制

使用[职先机主题页](https://jobs.ultraai.site/topics/agent)、[Agent工程与评测实验室JD索引](https://harness.zhigouread.com/career/jd-list)和公开搜索发现原始官方链接；只把这些页面视作导航，未采用其市场总量、词频统计、薪资估计、在招判断或技术趋势结论。对字节又尝试了精确job ID、精确中文标题以及 experienced/society 两种路径，仍无官方职责。浏览器补查尝试也返回“browser access host unavailable”，因此未把无法读取的问题伪装成已完成的核验。

## 跨JD能力矩阵：哪些应该进入个人项目

下列“项目证据”是研究推断，不是公司指定实现方案。列出代表岗位而不报无代表性的需求百分比。

| 能力 | 明确的一手岗位证据 | 应交付的项目证据 | 边界/优先级推断 |
|---|---|---|---|
| Agent运行内核/Harness | CN01、04、08、09、14、16、23 | 可检查的Loop；Task/Run/Step状态；结束条件与预算；可替换模型/工具适配；长任务失败归因 | 主干。不能仅把框架实例化称作自研Harness，应说明自己控制的边界与恢复语义。 |
| 工具、MCP、Skills与契约 | CN01、09、10、11、14、16、17、24、25 | 类型化工具I/O、失败分类、超时取消、工具版本；MCP server/client；技能前置条件和输出验收 | 主干。协议是集成机制，工具成功率与业务效果比接入数量更有说服力。 |
| 上下文、RAG与记忆 | CN08、09、11、14、15、18、19、22、23、24 | 混合检索/重排；上下文预算；压缩前后对比；任务状态和长期知识分离；有来源和失效机制的记忆 | 主干。通过消融证明收益；不要把所有东西都塞入向量库就称作记忆。 |
| 多Agent协作 | CN01、09、10、14、16、19、20、22、23、25、26 | 任务分解/路由、分支并行、消息契约、父子预算与取消、结果交接、冲突处理；与单Agent基线比较 | 主干但有条件启用。多角色提示词并列不足以证明协作价值。 |
| eval harness与评测驱动迭代 | CN04、06、07、09、18、19、20、24、26、27 | 真实任务集+隐藏测试；结果/工具/轨迹多层指标；确定性评分优先、校准的Judge辅助；回归门禁与badcase | 最重要的共同交付之一。运行时Harness与评测Harness分别设计、连接起来。 |
| 恢复、幂等与可靠性 | CN04、07、08、09、11、12、16、23、24 | checkpoint/事件记录；中断续跑；重试分类与幂等键；工具结果缓存；崩溃/超时/部分失败注入 | 深度来源。要说明副作用工具不能随意重放，而非仅记录对话。 |
| 观测与问题诊断 | CN01、02、09、10、11、12、16、23 | trace/run/span层级；结构化事件；token/成本/延迟分解；工具输入输出脱敏；回放与差异对比 | 主干。展示能从失败trace定位原因和验证改进。 |
| 沙箱、身份和确定性安全边界 | CN01、05、08、10、11、16、20、23、25 | 隔离执行、资源/网络限制、工具级授权、密钥隔离、人工确认；间接注入攻击任务与误拦截测试 | 主干。不能把system prompt或LLM自查当权限控制。 |
| 云端工程与产品交付 | CN04、10、11、12、13、16、17、21、23、25 | API+任务队列+持久化+取消恢复；容器部署；并发压测；可操作UI；反馈和版本治理 | 主干。个人项目可缩小规模，但需真实证明，不虚构大厂生产规模。 |
| 成本与推理性能 | CN01、03、06、09、10、18、24 | 每成功任务成本、P50/P95延迟、token分解、缓存命中、模型路由与受限并行 | 应用级优化应覆盖；CPU微架构/卡适配/万卡调度属于另一个专业轨道，不能声称项目完全覆盖。 |
| 数据飞轮、SFT/RL与持续进化 | CN07、12、15、18、19、22、26、27、28 | 轨迹清洗、失败标签、合成数据；可验证奖励；固定评测下SFT/RL小实验；模型/技能/Prompt版本与回滚 | 算法岗的重要方向；工程主线可扩展，但离线Prompt改写不能称作RL或模型训练。 |
| 用户/业务闭环与AI开发能力 | CN04、07、08、09、10、20、21、25、26、28 | 用户问题→验收标准→执行结果；真实使用反馈；个人贡献/设计取舍/复盘；AI生成代码也有测试审查 | 跨岗位要求。项目应有完整可验证任务结果，不能只有聊天演示或技术名词。 |

## 对项目选择的初步评估

1. **最强主线：面向可重复真实任务的Agent系统 + 可检查的执行Harness + 评测平台。** 选一个实际业务/研发域，把多Agent、工具、RAG/Memory、沙箱、状态恢复、追踪和评测连接成完整闭环。CN04/08/09/16/23/25的组合对此支持较强。
2. **适合做深的场景是研发/数据分析/故障诊断/研究交付等长程任务。** 这类任务容易设计工具与可验证交付物，能制造真实失败并比较单、多Agent；此为基于岗位职责的选择推断，不表示JD只招这些场景。
3. **算法扩展必须单列。** 可在同一系统上增设轨迹数据→SFT或可验证奖励RL→固定任务评估链路，用于接近CN07/15/18/19/26/27/28。没有训练实验，不应在简历写“覆盖Agent RL”。
4. **一个项目不可能覆盖所有岗位门槛。** 学历、一作论文、资深生产ownership、特定业务知识、CPU/推理内核、超大规模训练等不是增加功能即可替代。合理目标是覆盖工程岗位共同能力，再选择一个算法/性能/安全专长做可复现实验。
5. **“不过时”来自可换模型、可换协议适配与固定评测反馈。** 模型、框架和产品名会变化；可验证任务、工具契约、状态与副作用、权限边界、数据质量和实验方法更能长期迁移。这是研究判断，不是对未来技术稳定性的保证。

## 可持续补查顺序

- 首先手工/可用浏览器重新打开字节、蚂蚁、快手、月之暗面与DeepSeek的候选详情，补证据而非扩大未经核实的职责清单。
- 然后固定目标招聘类型（校招/实习/社招工程/算法）筛岗位；主表不同年限与方向不可直接相加为统一能力清单。
- 对目标岗位保留官网URL、岗位ID、访问日、页面显示日期和证据级别；再次求职时复检是否下线和职责变动。
- 若要计算覆盖率，先逐岗位标注“必需/优先/职责/未提及”，去除跨城市重复与同模板岗位，再按公司和岗位轨道分别统计；本轮不提供伪精确覆盖百分比。
