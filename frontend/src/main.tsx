import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Beaker,
  BookOpen,
  Box,
  Check,
  ChevronRight,
  Circle,
  Code2,
  FileCode2,
  FolderGit2,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Square,
  Terminal,
  Workflow,
  X,
} from "lucide-react";
import { api, artifactText, download, token } from "./api";
import type {
  Project,
  Issue,
  Run,
  RunDetail,
  Trace,
  Skill,
  Memory,
  Experiment,
  Report,
  ModelConfig,
} from "./api";
import "./style.css";

const labels: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  waiting_input: "等待输入",
  paused: "已暂停",
  verifying: "独立验证",
  succeeded: "已通过",
  failed: "未通过",
  cancelled: "已取消",
  accepted: "已验收",
  rejected: "已拒绝",
  completed: "已交付",
  intent: "待执行",
  reserved: "费用已预占",
  settled: "费用已结算",
  failed_unknown_usage: "失败，费用待核对",
  usage_missing: "用量缺失",
  supervisor: "主管",
  code_investigation: "代码调查",
  reproduction: "复现测试",
  implementation: "实现集成",
  single: "单 Agent",
  parallel: "独立并行调查",
  fixed: "固定协作",
  adaptive: "自适应委派",
};
const tr = (s: string) => labels[s] || s;
const short = (s: string) => s.slice(0, 8);
const date = (t: number) =>
  new Date(t * 1000).toLocaleString("zh-CN", { hour12: false });
const eventTitle = (kind: string) =>
  ({
    "run.queued": "运行已入队",
    "run.started": "开始执行",
    "lease.takeover": "执行租约已接管",
    "model.reserved": "模型调用预算已预占",
    "agent.reply": "Agent 返回决策",
    "tool.intent": "准备执行工具",
    "tool.result": "工具执行完成",
    "tool.error": "工具执行失败",
    "tool.rejected": "工具请求已拦截",
    "agent.progress": "Agent 进度已保存",
    "delegation.created": "创建委托任务",
    "delegation.accepted": "子任务产物已验收",
    "delegation.rejected": "子任务交付已拒绝",
    "delegation.reviewed": "主管完成委托验收",
    "verification.started": "启动独立验证",
    "verification.result": "独立验证结果已保存",
    "run.succeeded": "工单修复已通过",
    "run.failed": "运行未通过",
    "run.cancelled": "运行已取消",
    "run.paused": "运行已暂停",
    "control.pause": "已请求暂停",
    "control.resume": "已请求继续",
    "control.cancel": "已请求取消",
  })[kind] || kind;
function eventSummary(event: Trace) {
  const p = event.payload;
  if (p.reason) return String(p.reason);
  if (p.name)
    return `${p.name} · ${
      String(p.agent_id || "")
        .split("-")
        .slice(1)
        .join("-") || "主管"
    }`;
  if (p.action)
    return `${p.scripted_test ? "脚本化测试 · " : ""}${p.action === "finish" ? "请求交付与验收" : p.action === "delegate" ? "提交结构化委托" : "请求工具执行"}`;
  if (p.outcomes) return "子任务交付已核对产物、执行记录和作用域";
  if (p.artifact_id)
    return `执行证据 ${short(String(p.artifact_id))}${p.truncated ? " · 长输出已外置" : ""}`;
  if (p.role) return `${tr(String(p.role))} · ${String(p.objective || "")}`;
  if (p.done) return "进度与交付已持久化";
  if (p.epoch) return `执行租约 v${p.epoch}`;
  return "事件已记录，可展开查看完整执行数据。";
}
function Status({ value }: { value: string }) {
  return (
    <span className={`status ${value}`}>
      <span />
      {tr(value)}
    </span>
  );
}
function ScriptBadge() {
  return (
    <span className="script-badge">
      <Beaker size={12} />
      脚本化测试
    </span>
  );
}
function Empty({
  text,
  children,
}: {
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <Box size={32} />
      <p>{text}</p>
      {children}
    </div>
  );
}
function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const control = React.isValidElement(children)
    ? React.cloneElement(
        children as React.ReactElement<{ "aria-label"?: string }>,
        { "aria-label": label },
      )
    : children;
  return (
    <label className="field">
      <span>{label}</span>
      {control}
    </label>
  );
}
function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="关闭" onClick={close}>
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function App() {
  const [modelConfig, setModelConfig] = useState<ModelConfig | null>(null);
  const [modelConfigError, setModelConfigError] = useState("");
  const [page, setPage] = useState("overview"),
    [projects, setProjects] = useState<Project[]>([]),
    [issues, setIssues] = useState<Issue[]>([]),
    [runs, setRuns] = useState<Run[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]),
    [memories, setMemories] = useState<Memory[]>([]),
    [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selected, setSelected] = useState<string | null>(null),
    [detail, setDetail] = useState<RunDetail | null>(null),
    [events, setEvents] = useState<Trace[]>([]),
    [tab, setTab] = useState("timeline");
  const [error, setError] = useState(""),
    [online, setOnline] = useState(false),
    [busy, setBusy] = useState(false),
    [env, setEnv] = useState<{ docker: boolean; detail?: string } | null>(null);
  const [modal, setModal] = useState(""),
    [form, setForm] = useState<Record<string, string>>({}),
    [report, setReport] = useState<Report | null>(null),
    [viewArtifact, setViewArtifact] = useState<{
      title: string;
      content: string;
    } | null>(null);
  const [query, setQuery] = useState(""),
    [results, setResults] = useState<unknown[] | null>(null),
    [patch, setPatch] = useState("");
  const lastEvent = useRef(0);
  const refresh = useCallback(async () => {
    void api<ModelConfig>("/api/config")
      .then((config) => {
        setModelConfig(config);
        setModelConfigError("");
      })
      .catch(() =>
        setModelConfigError("读取模型配置失败，请重启更新后的后端。"),
      );
    try {
      const [p, i, r, s, m, e] = await Promise.all([
        api<Project[]>("/api/projects"),
        api<Issue[]>("/api/issues"),
        api<Run[]>("/api/runs"),
        api<Skill[]>("/api/skills"),
        api<Memory[]>("/api/memories"),
        api<Experiment[]>("/api/experiments"),
      ]);
      setProjects(p);
      setIssues(i);
      setRuns(r);
      setSkills(s);
      setMemories(m);
      setExperiments(e);
      setOnline(true);
    } catch (e) {
      setOnline(false);
      setError(String(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
    void api<{ docker: boolean; detail?: string }>("/api/environment")
      .then(setEnv)
      .catch(() => {});
    const id = setInterval(() => {
      void refresh();
    }, 5000);
    return () => clearInterval(id);
  }, [refresh]);
  useEffect(() => {
    if (!selected) return;
    let live = true;
    const update = () =>
      api<RunDetail>(`/api/runs/${selected}`)
        .then((d) => {
          if (live) setDetail(d);
        })
        .catch((e) => {
          if (live) setError(String(e));
        });
    void update();
    const id = setInterval(() => {
      void update();
    }, 2000);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [selected]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    lastEvent.current = 0;
    setEvents([]);
    async function subscribe() {
      while (!controller.signal.aborted) {
        try {
          const res = await fetch(`/api/runs/${selected}/events`, {
            headers: {
              Authorization: `Bearer ${token()}`,
              "Last-Event-ID": String(lastEvent.current),
            },
            signal: controller.signal,
          });
          if (!res.ok) throw new Error(`SSE ${res.status}`);
          const reader = res.body!.getReader(),
            decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let boundary;
            while ((boundary = buffer.indexOf("\n\n")) >= 0) {
              const block = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              const data = block
                .split("\n")
                .find((l) => l.startsWith("data: "));
              if (data) {
                const event = JSON.parse(data.slice(6)) as Trace;
                if (event.seq > lastEvent.current) {
                  lastEvent.current = event.seq;
                  setEvents((old) => [...old, event].slice(-500));
                }
              }
            }
          }
        } catch (e) {
          if (controller.signal.aborted) return;
          setError(
            `执行轨迹连接中断，将从事件 ${lastEvent.current} 续读：${String(e)}`,
          );
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
    }
    void subscribe();
    return () => controller.abort();
  }, [selected]);
  useEffect(() => {
    const p = detail?.artifacts.find((a) => a.kind === "patch");
    setPatch("");
    if (p)
      void artifactText(p.id)
        .then(setPatch)
        .catch((e) => setError(String(e)));
  }, [detail?.patch_hash]);
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const open = (name: string, defaults: Record<string, string> = {}) => {
    const contract = issues.find(
      (issue) => issue.id === defaults.issue,
    )?.contract;
    setForm({
      max_cost_cny: String(Math.min(1, contract?.max_cost_cny ?? 5)),
      max_calls: String(Math.min(20, contract?.max_calls ?? 60)),
      max_seconds: String(Math.min(600, contract?.max_seconds ?? 1200)),
      model_source: modelConfig?.default_source || "scripted",
      ...defaults,
    });
    setModal(name);
  };
  const selectedSource =
    form.model_source || modelConfig?.default_source || "scripted";
  const selectedContract = issues.find(
    (issue) => issue.id === form.issue,
  )?.contract;
  const modelProblem =
    modelConfig?.reason === "api_key_missing"
      ? "服务端未填写 DeepSeek API Key"
      : modelConfig?.reason === "price_snapshot_missing"
        ? "服务端尚未配置模型价格快照"
        : "服务端尚未启用真实模型模式";
  const input = (name: string) => ({
    value: form[name] || "",
    onChange: (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >,
    ) => setForm({ ...form, [name]: e.target.value }),
  });
  const selectRun = (id: string) => {
    setSelected(id);
    setDetail(null);
    setTab("timeline");
    setPage("runs");
  };
  const createDemo = () =>
    act(async () => {
      const data = await api<{ issue: Issue; environment_available: boolean }>(
        "/api/demo",
        {},
      );
      setPage("issues");
      if (!data.environment_available)
        setError(
          "开发夹具已创建。请先构建沙箱镜像；当前环境无法执行容器测试。",
        );
    });
  const title: Record<string, string> = {
    overview: "研发工单工作台",
    projects: "项目与仓库",
    issues: "工单管理",
    runs: "运行与交付",
    knowledge: "知识与 Skills",
    experiments: "实验比较",
  };
  const active = runs.filter((r) =>
    ["running", "verifying"].includes(r.status),
  );
  const runTable = (items: Run[]) => (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>工单 / 运行</th>
            <th>策略与来源</th>
            <th>状态</th>
            <th>模型费用</th>
            <th>创建时间</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr
              key={r.id}
              onClick={() => selectRun(r.id)}
              className="clickable"
            >
              <td>
                <strong>
                  {issues.find((i) => i.id === r.issue_id)?.contract.title ||
                    short(r.issue_id)}
                </strong>
                <small className="mono">{short(r.id)}</small>
              </td>
              <td>
                {tr(r.strategy)}
                <small>
                  {r.model_source === "scripted" ? <ScriptBadge /> : "DeepSeek"}
                </small>
              </td>
              <td>
                <Status value={r.status} />
                {r.control && <small>请求：{tr(r.control)}</small>}
              </td>
              <td className="mono">
                ¥ {r.spent.toFixed(3)}
                {r.reserved > 0 && <small>预占 ¥{r.reserved.toFixed(3)}</small>}
              </td>
              <td className="muted">{date(r.created_at)}</td>
              <td>
                <ChevronRight size={16} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!items.length && (
        <Empty text="还没有执行记录。创建工单后发起第一次运行。" />
      )}
    </div>
  );
  async function submitForm(e: React.FormEvent) {
    e.preventDefault();
    await act(async () => {
      if (modal === "project") {
        await api("/api/projects", {
          name: form.name,
          repository: form.repository,
          commit: form.commit || null,
        });
      }
      if (modal === "document") {
        await api(`/api/projects/${form.project}/documents`, {
          path: form.path,
          version: form.version,
          content: form.content,
        });
      }
      if (modal === "issue") {
        const project = projects.find((p) => p.id === form.project)!;
        await api("/api/issues", {
          project_id: project.id,
          title: form.title,
          description: form.description,
          base_commit: project.commit,
          snapshot_hash: project.snapshot_hash,
          environment: form.environment || "repairlab-sandbox:local",
          allowed_paths: (form.paths || "src/").split(",").map((s) => s.trim()),
          public_tests: (form.tests || "tests").split(",").map((s) => s.trim()),
          verifier_id: form.verifier || null,
          max_cost_cny: Number(form.max_cost_cny || 1),
          max_calls: Number(form.max_calls || 20),
          max_seconds: Number(form.max_seconds || 600),
          versions: {
            harness: "0.1.0",
            tools: "1",
            environment: form.envhash || "",
            verifier: form.verifierhash || "",
          },
        });
      }
      if (modal === "run") {
        const r = await api<Run>("/api/runs", {
          issue_id: form.issue,
          strategy: form.strategy || "single",
          model_source: selectedSource,
          script: form.script || "repair",
          limits: {
            max_cost_cny: Number(form.max_cost_cny || 1),
            max_calls: Number(form.max_calls || 20),
            max_seconds: Number(form.max_seconds || 600),
          },
        });
        selectRun(r.id);
      }
      if (modal === "experiment") {
        await api("/api/experiments", {
          name: form.name,
          issue_ids: [form.issue],
          strategies: (form.strategies || "single,adaptive").split(","),
          repetitions: Number(form.repetitions || 1),
          model_source: "scripted",
          script: "repair",
          formal: false,
        });
      }
      if (modal === "skill") {
        await api("/api/skills", { name: form.name, content: form.content });
      }
      if (modal === "memory") {
        await api("/api/memories", {
          project_id: form.project,
          content: form.content,
          source_artifacts: (form.artifacts || "").split(",").filter(Boolean),
          applicable_versions: (form.versions || "").split(",").filter(Boolean),
          invalidation_conditions: form.conditions,
          status: "candidate",
        });
      }
      if (modal === "memory-validate") {
        await api(`/api/memories/${form.id}/validate`, {
          run_ids: form.runs.split(",").map((s) => s.trim()),
        });
      }
      if (modal === "token") {
        localStorage.setItem("repairlab-token", form.token);
      }
      if (modal === "input") {
        await api(`/api/runs/${selected}/input`, { content: form.content });
      }
      setModal("");
    });
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("overview");
          }}
        >
          <div className="brand-icon">
            <GitBranch size={24} />
          </div>
          <div>
            RepairLab<small>研发工单 · 执行平台</small>
          </div>
        </a>
        <div className="workspace-label">
          LOCAL WORKSPACE <span>01</span>
        </div>
        <nav>
          {[
            { id: "overview", icon: LayoutDashboard, label: "工作台" },
            { id: "projects", icon: FolderGit2, label: "项目与仓库" },
            { id: "issues", icon: ListChecks, label: "工单管理" },
            { id: "runs", icon: Workflow, label: "运行与交付" },
            { id: "knowledge", icon: BookOpen, label: "知识与 Skills" },
            { id: "experiments", icon: Beaker, label: "实验比较" },
          ].map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "active" : ""}
              onClick={() => {
                setPage(n.id);
                if (n.id === "runs") setSelected(null);
              }}
            >
              <n.icon size={18} />
              {n.label}
              {n.id === "runs" && active.length > 0 && <b>{active.length}</b>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={20} />
            <strong>本地单用户环境</strong>
            <p>代码与执行证据保存在本机</p>
            <span className={online ? "connection connected" : "connection"}>
              <Circle size={7} fill="currentColor" />
              {online ? "后端已连接" : "后端未连接"}
            </span>
          </div>
          <button
            className="settings-button"
            onClick={() => open("token", { token: token() })}
          >
            <Settings size={16} />
            连接设置<span>v0.1</span>
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <span>工作空间</span>
            <ChevronRight size={14} />
            <strong>{title[page]}</strong>
          </div>
          <div className="top-meta">
            <span className="mono">LOCAL / DEV</span>
            <div className="avatar">RL</div>
          </div>
        </header>
        <main>
          <div className="safety-strip">
            <ShieldCheck size={16} />
            <strong>
              {!modelConfig
                ? "正在读取模型配置"
                : modelConfig.model_calls_enabled
                  ? "真实模型模式已启用"
                  : "真实模型调用已关闭"}
            </strong>
            <span>
              {modelConfigError ||
                (modelConfig?.model_calls_enabled
                  ? `${modelConfig.model} · ${modelConfig.model_ready ? "配置就绪" : modelProblem} · 调用受共享预算限制`
                  : "使用脚本化替身验证工程流程")}
            </span>
            {!modelConfig?.model_calls_enabled && <ScriptBadge />}
          </div>
          {error && (
            <div className="error" role="alert">
              <span>{error}</span>
              <button aria-label="关闭提示" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className="page-heading">
            <div>
              <div className="eyebrow">REPAIR OPERATIONS</div>
              <h1>{selected && page === "runs" ? "运行详情" : title[page]}</h1>
              <p>
                {page === "overview"
                  ? "从问题理解到独立验收，让每一步修复都有据可查。"
                  : page === "runs"
                    ? "执行轨迹、协作产物与独立验证，绑定同一份代码版本。"
                    : page === "knowledge"
                      ? "只复用有来源、版本范围和回归证据的经验。"
                      : "管理真实输入与执行记录，脚本化测试独立标记。"}
              </p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => void act(refresh)}
              >
                <RefreshCw size={15} />
                刷新
              </button>
              {page === "overview" || page === "issues" ? (
                <button
                  className="button primary"
                  onClick={() =>
                    open("issue", { project: projects[0]?.id || "" })
                  }
                >
                  <Plus size={16} />
                  新建工单
                </button>
              ) : page === "projects" ? (
                <button
                  className="button primary"
                  onClick={() => open("project")}
                >
                  <Plus size={16} />
                  登记项目
                </button>
              ) : page === "experiments" ? (
                <button
                  className="button primary"
                  onClick={() =>
                    open("experiment", {
                      issue: issues[0]?.id || "",
                      strategies: "single,adaptive",
                      repetitions: "1",
                    })
                  }
                >
                  <Plus size={16} />
                  配置实验
                </button>
              ) : null}
            </div>
          </div>
          {page === "overview" && (
            <>
              <div className="stats">
                <div>
                  <span>
                    项目仓库 <FolderGit2 size={17} />
                  </span>
                  <strong>{projects.length.toString().padStart(2, "0")}</strong>
                  <small>固定版本 · 可追溯快照</small>
                </div>
                <div>
                  <span>
                    研发工单 <ListChecks size={17} />
                  </span>
                  <strong>{issues.length.toString().padStart(2, "0")}</strong>
                  <small>
                    {
                      issues.filter(
                        (i) => i.contract.source === "development_fixture",
                      ).length
                    }{" "}
                    个开发夹具
                  </small>
                </div>
                <div>
                  <span>
                    执行中 <Activity size={17} />
                  </span>
                  <strong className="green">
                    {active.length.toString().padStart(2, "0")}
                  </strong>
                  <small>
                    队列中 {runs.filter((r) => r.status === "queued").length} ·
                    暂停 {runs.filter((r) => r.status === "paused").length}
                  </small>
                </div>
                <div>
                  <span>
                    累计模型费用 <span>¥</span>
                  </span>
                  <strong>
                    {runs.reduce((s, r) => s + r.spent, 0).toFixed(2)}
                  </strong>
                  <small>脚本化测试不产生模型费用</small>
                </div>
              </div>
              <div className="overview-grid">
                <section className="panel execution-panel">
                  <div className="section-head">
                    <h2>
                      <Workflow size={18} />
                      修复执行链路
                    </h2>
                    <span className="subtle-tag">EVIDENCE FIRST</span>
                  </div>
                  <div className="pipeline">
                    {[
                      {
                        n: "01",
                        icon: Search,
                        title: "理解与定位",
                        desc: "工单契约 / 代码证据",
                      },
                      {
                        n: "02",
                        icon: Terminal,
                        title: "问题复现",
                        desc: "隔离环境 / 执行记录",
                      },
                      {
                        n: "03",
                        icon: FileCode2,
                        title: "修复与集成",
                        desc: "独立工作区 / 最终补丁",
                      },
                      {
                        n: "04",
                        icon: ShieldCheck,
                        title: "独立验收",
                        desc: "全新容器 / 版本绑定",
                      },
                    ].map((s, i) => (
                      <React.Fragment key={s.n}>
                        <div>
                          <span className="step-number">{s.n}</span>
                          <div className="step-icon">
                            <s.icon size={21} />
                          </div>
                          <strong>{s.title}</strong>
                          <small>{s.desc}</small>
                        </div>
                        {i < 3 && (
                          <ArrowRight className="step-arrow" size={16} />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                  <div className="execution-foot">
                    <span>
                      <span className="dot" />
                      默认单 Agent，按证据决定是否委派
                    </span>
                    <span>最多 2 个并发子任务</span>
                  </div>
                </section>
                <section className="panel setup-panel">
                  <div className="section-head">
                    <h2>本地环境</h2>
                    <Box size={18} />
                  </div>
                  <div className="env-line">
                    <span>API 服务</span>
                    <Status value={online ? "succeeded" : "failed"} />
                  </div>
                  <div className="env-line">
                    <span>Docker 测试镜像</span>
                    <span className={env?.docker ? "text-green" : "text-amber"}>
                      {env === null ? "检查中" : env.docker ? "可用" : "不可用"}
                    </span>
                  </div>
                  <div className="env-line">
                    <span>真实模型</span>
                    <span className="muted">
                      {modelConfig?.model_ready
                        ? "已启用"
                        : modelConfig?.model_calls_enabled
                          ? "配置未就绪"
                          : "已禁用"}
                    </span>
                  </div>
                  <button
                    className="demo-button"
                    disabled={busy || !online}
                    onClick={() => void createDemo()}
                  >
                    <Plus size={15} />
                    导入本地开发夹具
                    <ArrowRight size={15} />
                  </button>
                </section>
              </div>
              <section className="panel">
                <div className="section-head">
                  <h2>
                    最近运行 <span className="count">{runs.length}</span>
                  </h2>
                  <button
                    className="text-button"
                    onClick={() => setPage("runs")}
                  >
                    查看全部
                    <ArrowRight size={14} />
                  </button>
                </div>
                {runTable(runs.slice(0, 6))}
              </section>
              <div className="footnote">
                <Beaker size={14} />
                脚本化测试与真实模型运行分别记录；补丁通过独立验收后才记为成功。
              </div>
            </>
          )}
          {page === "projects" && (
            <>
              <div className="card-grid">
                {projects.map((p) => (
                  <section className="panel project-card" key={p.id}>
                    <div className="project-icon">
                      <FolderGit2 size={24} />
                    </div>
                    <h2>{p.name}</h2>
                    <p className="mono">{p.repository}</p>
                    <div className="meta-pair">
                      <span>代码版本</span>
                      <code>{p.commit}</code>
                    </div>
                    <div className="meta-pair">
                      <span>输入快照</span>
                      <code>{short(p.snapshot_hash)}</code>
                    </div>
                    <button
                      className="button secondary"
                      onClick={() =>
                        void act(async () => {
                          await api(`/api/projects/${p.id}/index`, {});
                        })
                      }
                    >
                      重建文本与符号索引
                    </button>
                    <button
                      className="text-button"
                      onClick={() =>
                        open("document", { project: p.id, version: "v1" })
                      }
                    >
                      添加版本化文档 <Plus size={13} />
                    </button>
                  </section>
                ))}
              </div>
              {!projects.length && (
                <section className="panel">
                  <Empty text="登记本地仓库，或导入开发夹具开始体验。">
                    <button
                      className="button primary"
                      onClick={() => void createDemo()}
                    >
                      导入开发夹具
                    </button>
                  </Empty>
                </section>
              )}
              <section className="panel search-panel">
                <h2>版本范围检索</h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void act(async () =>
                      setResults(
                        await api<unknown[]>(
                          `/api/projects/${form.searchProject || projects[0]?.id}/search?query=${encodeURIComponent(query)}`,
                        ),
                      ),
                    );
                  }}
                >
                  <select
                    aria-label="检索项目"
                    value={form.searchProject || projects[0]?.id || ""}
                    onChange={(e) =>
                      setForm({ ...form, searchProject: e.target.value })
                    }
                  >
                    {projects.map((p) => (
                      <option value={p.id} key={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="检索内容"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜索代码、符号或文档…"
                    required
                  />
                  <button
                    className="button primary"
                    disabled={!projects.length}
                  >
                    <Search size={16} />
                    检索
                  </button>
                </form>
                {results && <pre>{JSON.stringify(results, null, 2)}</pre>}
              </section>
            </>
          )}
          {page === "issues" && (
            <section className="panel">
              <div className="section-head">
                <h2>
                  全部工单<span className="count">{issues.length}</span>
                </h2>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void createDemo()}
                >
                  <Beaker size={15} />
                  导入开发夹具
                </button>
              </div>
              {issues.map((i) => (
                <article className="issue-row" key={i.id}>
                  <div className="issue-symbol">
                    <ListChecks size={20} />
                  </div>
                  <div>
                    <div className="inline">
                      <h3>{i.contract.title}</h3>
                      {i.contract.source === "development_fixture" && (
                        <ScriptBadge />
                      )}
                    </div>
                    <p>{i.contract.description}</p>
                    <small className="mono">
                      {projects.find((p) => p.id === i.project_id)?.name} ·{" "}
                      {short(i.contract.base_commit)} · {short(i.id)}
                    </small>
                  </div>
                  <button
                    className="button secondary"
                    onClick={() =>
                      open("run", {
                        issue: i.id,
                        strategy: "single",
                        script: "repair",
                      })
                    }
                  >
                    <Play size={14} />
                    发起运行
                  </button>
                </article>
              ))}
              {!issues.length && (
                <Empty text="还没有工单。先登记仓库，保存问题描述和验收契约。" />
              )}
            </section>
          )}
          {page === "runs" && !selected && (
            <section className="panel">
              <div className="section-head">
                <h2>全部运行</h2>
                <button
                  className="text-button"
                  onClick={() =>
                    open("run", {
                      issue: issues[0]?.id || "",
                      strategy: "single",
                      script: "repair",
                    })
                  }
                >
                  <Plus size={15} />
                  发起运行
                </button>
              </div>
              {runTable(runs)}
            </section>
          )}
          {page === "runs" &&
            selected &&
            (!detail ? (
              <Empty text="正在读取运行账本…" />
            ) : (
              <>
                <button
                  className="text-button back"
                  onClick={() => setSelected(null)}
                >
                  ← 返回运行列表
                </button>
                <section className="panel run-summary">
                  <div>
                    <div className="inline">
                      <h2>
                        {issues.find((i) => i.id === detail.issue_id)?.contract
                          .title || "工单修复"}
                      </h2>
                      <Status value={detail.status} />
                      {detail.scripted_test && <ScriptBadge />}
                    </div>
                    <p className="mono">
                      RUN {detail.id} · {tr(detail.strategy)}
                    </p>
                    {detail.terminal_reason && (
                      <div className="reason">
                        终止原因：{detail.terminal_reason}
                        {detail.status !== "succeeded" && " · 已保留部分交付"}
                      </div>
                    )}
                  </div>
                  <div className="run-actions">
                    {["running", "queued", "verifying"].includes(
                      detail.status,
                    ) && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          void act(() =>
                            api(`/api/runs/${selected}/control/pause`, {}),
                          )
                        }
                      >
                        <Pause size={14} />
                        暂停
                      </button>
                    )}
                    {["paused", "waiting_input"].includes(detail.status) && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          detail.status === "waiting_input"
                            ? open("input")
                            : void act(() =>
                                api(`/api/runs/${selected}/control/resume`, {}),
                              )
                        }
                      >
                        <Play size={14} />
                        继续
                      </button>
                    )}
                    {!["succeeded", "failed", "cancelled"].includes(
                      detail.status,
                    ) && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          void act(() =>
                            api(`/api/runs/${selected}/control/cancel`, {}),
                          )
                        }
                      >
                        <Square size={13} />
                        取消
                      </button>
                    )}
                    {["failed", "cancelled"].includes(detail.status) && (
                      <button
                        className="button secondary"
                        onClick={() =>
                          void act(async () => {
                            const r = await api<Run>(
                              `/api/runs/${selected}/control/retry`,
                              {},
                            );
                            selectRun(r.id);
                          })
                        }
                      >
                        <RefreshCw size={14} />
                        新建重试
                      </button>
                    )}
                    <button
                      className="button secondary"
                      onClick={() =>
                        void act(() =>
                          download(
                            `/api/runs/${selected}/export`,
                            `run-${selected}.json`,
                          ),
                        )
                      }
                    >
                      <ArrowDownToLine size={15} />
                      导出
                    </button>
                  </div>
                </section>
                <div className="run-metrics">
                  <span>
                    <strong>{detail.calls}</strong>模型循环
                  </span>
                  <span>
                    <strong>{detail.agents.length}</strong>Agent
                  </span>
                  <span>
                    <strong>{detail.receipts.length}</strong>工具记录
                  </span>
                  <span>
                    <strong>{Math.round(detail.elapsed_seconds)}s</strong>
                    执行耗时
                  </span>
                  <span>
                    <strong>¥{detail.spent.toFixed(3)}</strong>模型费用 / 预占 ¥
                    {detail.reserved.toFixed(3)}
                  </span>
                </div>
                <section className="panel">
                  <div className="tabs">
                    {[
                      ["timeline", "执行时间线"],
                      ["agents", "Agent 关系图"],
                      ["tools", "工具与证据"],
                      ["patch", "补丁与验收"],
                    ].map(([id, name]) => (
                      <button
                        key={id}
                        onClick={() => setTab(id)}
                        className={tab === id ? "selected" : ""}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                  {tab === "timeline" && (
                    <div className="timeline">
                      {events.map((e) => (
                        <article key={e.seq}>
                          <div className="timeline-node">
                            <Check size={11} />
                          </div>
                          <div className="event-title">
                            <strong>{eventTitle(e.kind)}</strong>
                            <span className="mono">
                              #{e.seq} · {date(e.created_at)}
                            </span>
                          </div>
                          <p className="event-summary">{eventSummary(e)}</p>
                          <details>
                            <summary>执行数据 · {e.kind}</summary>
                            <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                          </details>
                        </article>
                      ))}
                      {!events.length && (
                        <Empty text="等待执行事件。SSE 连接将自动续读。" />
                      )}
                    </div>
                  )}
                  {tab === "agents" && (
                    <div className="agent-tree">
                      {detail.agents.map((a) => (
                        <div
                          key={a.id}
                          className={`agent-card ${a.parent_id ? "child" : ""}`}
                        >
                          <div className="inline">
                            <div className="agent-icon">
                              <GitBranch size={18} />
                            </div>
                            <strong>{tr(a.role)}</strong>
                            <Status value={a.status} />
                          </div>
                          <small className="mono">
                            {a.key} · {short(a.id)}
                          </small>
                          <p>{a.summary || "等待执行与产物验收"}</p>
                          <span>{a.artifacts.length} 个已接受产物</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {tab === "tools" && (
                    <div className="evidence-grid">
                      <div>
                        <h3>工具动作账本</h3>
                        {detail.receipts.map((r) => (
                          <details key={r.id}>
                            <summary>
                              <code>{r.name}</code>
                              <Status value={r.status} />
                              <small>{short(r.id)}</small>
                            </summary>
                            <pre>
                              {JSON.stringify(
                                { arguments: r.arguments, result: r.result },
                                null,
                                2,
                              )}
                            </pre>
                          </details>
                        ))}
                      </div>
                      <div>
                        <h3>持久化产物</h3>
                        {detail.artifacts.map((a) => (
                          <button
                            key={a.id}
                            className="artifact-row"
                            onClick={() =>
                              void act(async () =>
                                setViewArtifact({
                                  title: a.kind,
                                  content: await artifactText(a.id),
                                }),
                              )
                            }
                          >
                            <FileCode2 size={17} />
                            <span>
                              <strong>{a.kind}</strong>
                              <small className="mono">
                                {short(a.sha256)} · {a.size} B
                              </small>
                            </span>
                            <ChevronRight size={14} />
                          </button>
                        ))}
                        <h3 style={{ marginTop: 24 }}>模型调用与计费</h3>
                        {(detail.model_calls || []).map((call) => (
                          <details key={call.id}>
                            <summary>
                              <code>{short(call.id)}</code>
                              <Status value={call.status} />
                            </summary>
                            <p className="muted">
                              已结算 ¥{call.actual?.toFixed(6) ?? "未知"} ·
                              调用前预占 ¥{call.reserved.toFixed(6)}
                            </p>
                            {call.metadata_json.error && (
                              <pre>
                                {JSON.stringify(
                                  call.metadata_json.error,
                                  null,
                                  2,
                                )}
                              </pre>
                            )}
                            <pre>
                              {JSON.stringify(
                                call.metadata_json.usage || {},
                                null,
                                2,
                              )}
                            </pre>
                          </details>
                        ))}
                      </div>
                    </div>
                  )}
                  {tab === "patch" && (
                    <div className="patch-view">
                      <div className="inline">
                        <h3>最终补丁</h3>
                        <code>
                          {detail.patch_hash
                            ? short(detail.patch_hash)
                            : "尚未导出"}
                        </code>
                      </div>
                      <pre className="diff">
                        {patch
                          ? patch.split("\n").map((line, i) => (
                              <div
                                key={i}
                                className={
                                  line.startsWith("+")
                                    ? "added"
                                    : line.startsWith("-")
                                      ? "removed"
                                      : ""
                                }
                              >
                                {line || " "}
                              </div>
                            ))
                          : "尚无最终补丁；失败时仍可在工具产物中查看执行证据。"}
                      </pre>
                      <h3>独立验证记录</h3>
                      {detail.verifications.map((v) => (
                        <div className="verification" key={v.id}>
                          <div className="inline">
                            <ShieldCheck size={20} />
                            <Status value={v.passed ? "succeeded" : "failed"} />
                            <strong>{v.reason}</strong>
                            {v.patch_hash !== detail.patch_hash && (
                              <b className="text-amber">过期结果</b>
                            )}
                          </div>
                          <div className="mono">
                            PATCH {short(v.patch_hash)} · ENV{" "}
                            {short(v.environment_hash)} · VERIFIER{" "}
                            {short(v.verifier_hash)}
                          </div>
                          <button
                            className="text-button"
                            onClick={() =>
                              void act(async () =>
                                setViewArtifact({
                                  title: "独立验证输出",
                                  content: await artifactText(v.artifact_id),
                                }),
                              )
                            }
                          >
                            查看执行输出
                            <ArrowRight size={14} />
                          </button>
                        </div>
                      ))}
                      {!detail.verifications.length && (
                        <p className="muted">
                          尚未执行独立验收。完成文字不代表测试通过。
                        </p>
                      )}
                    </div>
                  )}
                </section>
              </>
            ))}
          {page === "knowledge" && (
            <>
              <div className="section-heading">
                <h2>版本化 Skills</h2>
                <button
                  className="button secondary"
                  onClick={() => open("skill", { name: "analyze" })}
                >
                  <Plus size={15} />
                  创建新版本
                </button>
              </div>
              <div className="card-grid skills-grid">
                {skills
                  .filter((s) => s.active)
                  .map((s) => (
                    <section className="panel skill-card" key={s.id}>
                      <div className="inline">
                        <BookOpen size={20} />
                        <h3>{s.name}</h3>
                        <code>v{s.version}</code>
                      </div>
                      <p>{s.content}</p>
                      <small className="mono">{short(s.sha256)}</small>
                      <button
                        className="text-button"
                        onClick={() =>
                          open("skill", { name: s.name, content: s.content })
                        }
                      >
                        修订版本
                        <ArrowRight size={13} />
                      </button>
                      <button
                        className="text-button danger"
                        onClick={() =>
                          void act(() =>
                            api(`/api/skills/${s.id}/invalidate`, {}),
                          )
                        }
                      >
                        停用
                      </button>
                    </section>
                  ))}
              </div>
              <section className="panel">
                <div className="section-head">
                  <h2>
                    经验管理 <span className="count">{memories.length}</span>
                  </h2>
                  <button
                    className="text-button"
                    onClick={() =>
                      open("memory", { project: projects[0]?.id || "" })
                    }
                  >
                    <Plus size={15} />
                    新增候选经验
                  </button>
                </div>
                {memories.map((m) => (
                  <article className="memory-row" key={m.id}>
                    <Status value={m.status} />
                    <p>{m.entry.content}</p>
                    <small>
                      适用版本：{m.entry.applicable_versions.join(", ")} ·
                      失效条件：{m.entry.invalidation_conditions}
                    </small>
                    <div className="inline">
                      {m.status === "candidate" && (
                        <button
                          className="text-button"
                          onClick={() => open("memory-validate", { id: m.id })}
                        >
                          提交回归证据
                        </button>
                      )}
                      {m.status !== "invalid" && (
                        <button
                          className="text-button danger"
                          onClick={() =>
                            void act(() =>
                              api(`/api/memories/${m.id}/invalidate`, {}),
                            )
                          }
                        >
                          标记失效
                        </button>
                      )}
                    </div>
                  </article>
                ))}
                {!memories.length && (
                  <Empty text="候选经验通过跨工单回归后才可复用。参考解与隐藏验证产物不能作为经验来源。" />
                )}
              </section>
              <details className="panel history">
                <summary>全部 Skills 版本记录</summary>
                {skills.map((s) => (
                  <div className="meta-pair" key={s.id}>
                    <code>{s.id}</code>
                    <span>
                      {s.active ? "使用中" : "已停用"} · {short(s.sha256)}
                    </span>
                  </div>
                ))}
              </details>
            </>
          )}
          {page === "experiments" && (
            <>
              <div className="experiment-note">
                <Beaker size={20} />
                <div>
                  <strong>工程实验与正式实验分开统计</strong>
                  <p>
                    当前仅执行脚本化测试，用于验证调度和验收行为，不反映模型修复能力。
                  </p>
                </div>
              </div>
              <div className="card-grid">
                {experiments.map((e) => (
                  <section className="panel" key={e.id}>
                    <div className="section-head">
                      <h2>{e.name}</h2>
                      {e.config.model_source === "scripted" && <ScriptBadge />}
                    </div>
                    <div className="experiment-content">
                      <p>{e.config.strategies.map(tr).join(" / ")}</p>
                      <p className="muted">
                        每任务每策略 {e.config.repetitions} 次
                      </p>
                      <div className="inline">
                        <button
                          className="button secondary"
                          onClick={() =>
                            void act(() =>
                              api(`/api/experiments/${e.id}/launch`, {}),
                            )
                          }
                        >
                          <Play size={14} />
                          提交运行
                        </button>
                        <button
                          className="button secondary"
                          onClick={() =>
                            void act(async () =>
                              setReport(
                                await api<Report>(
                                  `/api/experiments/${e.id}/report`,
                                ),
                              ),
                            )
                          }
                        >
                          比较结果
                        </button>
                        <button
                          className="icon-button"
                          aria-label="导出实验"
                          onClick={() =>
                            void act(() =>
                              download(
                                `/api/experiments/${e.id}/report?download=true`,
                                `experiment-${e.id}.json`,
                              ),
                            )
                          }
                        >
                          <ArrowDownToLine size={18} />
                        </button>
                      </div>
                    </div>
                  </section>
                ))}
              </div>
              {!experiments.length && (
                <section className="panel">
                  <Empty text="配置共享模型、工具权限和总预算的对照实验。" />
                </section>
              )}
              {report && (
                <section className="panel">
                  <div className="section-head">
                    <h2>逐策略结果</h2>
                    {report.scripted_test && <ScriptBadge />}
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>策略</th>
                          <th>完成 / 提交</th>
                          <th>通过次数</th>
                          <th>模型费用</th>
                          <th>预占费用</th>
                          <th>失败分类</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(report.groups).map(([s, g]) => (
                          <tr key={s}>
                            <td>{tr(s)}</td>
                            <td>
                              {g.completed} / {g.total}
                            </td>
                            <td>{g.succeeded}</td>
                            <td>¥{g.cost_cny.toFixed(3)}</td>
                            <td>¥{g.reserved_cny.toFixed(3)}</td>
                            <td>{JSON.stringify(g.failures)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="footnote">
                    以上是实际账本记录；脚本化通过次数不能表述为模型成功率。
                  </p>
                </section>
              )}
            </>
          )}
          <footer>
            <span>RepairLab / Evidence before completion</span>
            <span>本地执行 · 可恢复账本 · 独立验收</span>
          </footer>
        </main>
      </div>
      {busy && (
        <div className="busy">
          <Loader2 size={16} className="spin" />
          正在处理…
        </div>
      )}
      {modal && (
        <Modal
          title={
            {
              project: "登记项目",
              document: "添加版本化文档",
              issue: "新建工单",
              run: "发起运行",
              experiment: "配置工程实验",
              skill: "创建 Skill 版本",
              memory: "新增候选经验",
              "memory-validate": "验证候选经验",
              token: "连接设置",
              input: "补充运行输入",
            }[modal] || modal
          }
          close={() => setModal("")}
        >
          <form onSubmit={(e) => void submitForm(e)}>
            {modal === "document" && (
              <>
                <Field label="文档路径">
                  <input
                    required
                    {...input("path")}
                    placeholder="docs/design.md"
                  />
                </Field>
                <Field label="文档版本">
                  <input required {...input("version")} />
                </Field>
                <Field label="公开文档内容">
                  <textarea required rows={8} {...input("content")} />
                </Field>
                <p className="muted">
                  文档会参与项目检索；创建新工单时将保存内容与版本快照。
                </p>
              </>
            )}
            {modal === "project" && (
              <>
                <Field label="项目名称">
                  <input required {...input("name")} />
                </Field>
                <Field label="仓库路径（相对 REPOSITORY_ROOT）">
                  <input
                    required
                    {...input("repository")}
                    placeholder="calculator"
                  />
                </Field>
                <Field label="固定 commit（开发夹具可填 fixture-v1）">
                  <input {...input("commit")} placeholder="完整 commit SHA" />
                </Field>
              </>
            )}
            {["issue", "memory"].includes(modal) && (
              <Field label="项目">
                <select
                  required
                  {...input("project")}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      project: e.target.value,
                      ...(modal === "issue"
                        ? {
                            template: "",
                            verifier: "",
                            verifierhash: "",
                            envhash: "",
                          }
                        : {}),
                    })
                  }
                >
                  <option value="">选择项目</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {modal === "issue" && (
              <>
                <Field label="执行环境与验收模板（同项目）">
                  <select
                    value={form.template || ""}
                    onChange={(e) => {
                      const template = issues.find(
                        (issue) => issue.id === e.target.value,
                      )?.contract;
                      setForm({
                        ...form,
                        template: e.target.value,
                        ...(template
                          ? {
                              environment: template.environment,
                              paths: template.allowed_paths.join(","),
                              tests: template.public_tests.join(","),
                              verifier: template.verifier_id || "",
                              verifierhash: template.versions.verifier || "",
                              envhash: template.versions.environment || "",
                            }
                          : { verifier: "", verifierhash: "", envhash: "" }),
                      });
                    }}
                  >
                    <option value="">手动配置环境与验证器</option>
                    {issues
                      .filter((issue) => issue.project_id === form.project)
                      .map((issue) => (
                        <option value={issue.id} key={issue.id}>
                          {issue.contract.title}
                        </option>
                      ))}
                  </select>
                </Field>
                <p className="muted">
                  同项目、相同验收条件可复用模板；新问题需要对应的独立测试。
                </p>
                <Field label="工单标题">
                  <input required {...input("title")} />
                </Field>
                <Field label="问题描述与验收条件">
                  <textarea required rows={4} {...input("description")} />
                </Field>
                <Field label="环境镜像">
                  <input
                    {...input("environment")}
                    placeholder="repairlab-sandbox:local"
                  />
                </Field>
                <div className="form-grid">
                  <Field label="允许修改路径（逗号分隔）">
                    <input {...input("paths")} placeholder="src/" />
                  </Field>
                  <Field label="公开测试路径">
                    <input {...input("tests")} placeholder="tests" />
                  </Field>
                </div>
                <details>
                  <summary>独立验收版本（由任务导入器生成）</summary>
                  <Field label="Verifier ID">
                    <input {...input("verifier")} />
                  </Field>
                  <Field label="Verifier SHA256">
                    <input {...input("verifierhash")} />
                  </Field>
                  <Field label="Environment image ID">
                    <input {...input("envhash")} />
                  </Field>
                </details>
                <p className="muted">
                  未配置验证器的运行将明确失败。开发夹具可从工单列表一键导入。
                </p>
              </>
            )}
            {["run", "experiment"].includes(modal) && (
              <Field label="工单">
                <select
                  required
                  {...input("issue")}
                  onChange={(e) => {
                    const next = issues.find(
                      (issue) => issue.id === e.target.value,
                    )?.contract;
                    setForm({
                      ...form,
                      issue: e.target.value,
                      max_cost_cny: String(
                        Math.min(
                          Number(form.max_cost_cny || 1),
                          next?.max_cost_cny ?? 5,
                        ),
                      ),
                      max_calls: String(
                        Math.min(
                          Number(form.max_calls || 20),
                          next?.max_calls ?? 60,
                        ),
                      ),
                      max_seconds: String(
                        Math.min(
                          Number(form.max_seconds || 600),
                          next?.max_seconds ?? 1200,
                        ),
                      ),
                    });
                  }}
                >
                  <option value="">选择工单</option>
                  {issues.map((i) => (
                    <option value={i.id} key={i.id}>
                      {i.contract.title}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            {modal === "run" && (
              <>
                <Field label="模型来源">
                  <select
                    value={selectedSource}
                    onChange={(e) =>
                      setForm({ ...form, model_source: e.target.value })
                    }
                  >
                    <option
                      value="scripted"
                      disabled={
                        selectedContract?.source !== "development_fixture"
                      }
                    >
                      脚本化测试（仅开发夹具）
                    </option>
                    <option
                      value="deepseek"
                      disabled={!modelConfig?.model_ready}
                    >
                      DeepSeek 真实模型
                      {!modelConfig?.model_ready ? "（服务端未就绪）" : ""}
                    </option>
                  </select>
                </Field>
                {selectedSource === "deepseek" && !modelConfig?.model_ready && (
                  <p role="alert" className="text-amber">
                    {modelProblem}；请配置 .env 后用 -EnableModelCalls
                    启动服务。
                  </p>
                )}
                <Field label="执行策略">
                  <select {...input("strategy")}>
                    {["single", "parallel", "fixed", "adaptive"].map((s) => (
                      <option key={s} value={s}>
                        {tr(s)}
                      </option>
                    ))}
                  </select>
                </Field>
                {selectedSource === "scripted" && (
                  <Field label="开发脚本">
                    <select {...input("script")}>
                      {["repair", "empty", "wrong", "injection"].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </Field>
                )}
                <div className="form-note">
                  {selectedSource === "scripted" ? (
                    <>
                      <ScriptBadge /> 替身驱动工具和验收流程。
                    </>
                  ) : (
                    <>
                      本次将调用 {modelConfig?.model} 并产生费用；父子 Agent
                      共用以下预算。
                    </>
                  )}
                  需要启动独立 worker。
                </div>
              </>
            )}
            {["issue", "run"].includes(modal) && (
              <div className="form-grid">
                <Field label="费用上限（元）">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={
                      modal === "run" ? selectedContract?.max_cost_cny || 5 : 5
                    }
                    required
                    {...input("max_cost_cny")}
                  />
                </Field>
                <Field label="最多模型调用次数">
                  <input
                    type="number"
                    min="1"
                    max={
                      modal === "run" ? selectedContract?.max_calls || 60 : 60
                    }
                    required
                    {...input("max_calls")}
                  />
                </Field>
                <Field label="执行期限（秒）">
                  <input
                    type="number"
                    min="1"
                    max={
                      modal === "run"
                        ? selectedContract?.max_seconds || 1200
                        : 1200
                    }
                    required
                    {...input("max_seconds")}
                  />
                </Field>
              </div>
            )}
            {modal === "experiment" && (
              <>
                <Field label="实验名称">
                  <input required {...input("name")} />
                </Field>
                <Field label="策略（逗号分隔）">
                  <input required {...input("strategies")} />
                </Field>
                <Field label="重复次数">
                  <input
                    type="number"
                    min="1"
                    max="3"
                    required
                    {...input("repetitions")}
                  />
                </Field>
              </>
            )}
            {modal === "skill" && (
              <>
                <Field label="Skill">
                  <select {...input("name")}>
                    {["reproduce", "analyze", "repair", "verify"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </Field>
                <Field label="可复用步骤与完成条件">
                  <textarea
                    required
                    minLength={30}
                    rows={8}
                    {...input("content")}
                  />
                </Field>
              </>
            )}
            {modal === "memory" && (
              <>
                <Field label="通用经验（不含任务答案或代码）">
                  <textarea required rows={4} {...input("content")} />
                </Field>
                <Field label="公开证据产物 ID（逗号分隔）">
                  <input required {...input("artifacts")} />
                </Field>
                <Field label="适用 commit（逗号分隔）">
                  <input required {...input("versions")} />
                </Field>
                <Field label="失效条件">
                  <input required {...input("conditions")} />
                </Field>
              </>
            )}
            {modal === "memory-validate" && (
              <Field label="两个不同工单的成功运行 ID（逗号分隔）">
                <input required {...input("runs")} />
              </Field>
            )}
            {modal === "token" && (
              <Field label="本地 API Token">
                <input
                  type="password"
                  autoComplete="off"
                  required
                  {...input("token")}
                />
              </Field>
            )}
            {modal === "input" && (
              <Field label="补充约束或材料">
                <textarea required rows={5} {...input("content")} />
              </Field>
            )}
            <div className="modal-actions">
              <button
                type="button"
                className="button secondary"
                onClick={() => setModal("")}
              >
                取消
              </button>
              <button
                className="button primary"
                disabled={
                  busy ||
                  (modal === "run" &&
                    (selectedSource === "deepseek"
                      ? !modelConfig?.model_ready
                      : selectedContract?.source !== "development_fixture"))
                }
              >
                {modal === "run" && selectedSource === "deepseek"
                  ? "发起真实模型运行"
                  : "保存并继续"}
                <ArrowRight size={14} />
              </button>
            </div>
          </form>
        </Modal>
      )}
      {viewArtifact && (
        <Modal title={viewArtifact.title} close={() => setViewArtifact(null)}>
          <pre className="artifact-content">{viewArtifact.content}</pre>
        </Modal>
      )}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
