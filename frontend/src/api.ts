export const token = () =>
  localStorage.getItem("repairlab-token") || "local-dev-change-me";
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token()}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      message = (await res.json()).detail || message;
    } catch {
      /* status remains visible */
    }
    throw new Error(message);
  }
  return res.json();
}
export async function artifactText(id: string) {
  const res = await fetch(`/api/artifacts/${id}`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!res.ok) throw new Error(`产物读取失败：${res.status}`);
  return res.text();
}
export async function download(path: string, name: string) {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!res.ok) throw new Error(`导出失败：${res.status}`);
  const href = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = href;
  a.download = name;
  a.click();
  URL.revokeObjectURL(href);
}
export interface Project {
  id: string;
  name: string;
  repository: string;
  commit: string;
  snapshot_hash: string;
}
export interface ModelConfig {
  model_calls_enabled: boolean;
  model_ready: boolean;
  api_key_configured: boolean;
  price_configured: boolean;
  model: string;
  default_source: "scripted" | "deepseek";
  reason: string | null;
  global_budget_cny: number;
}
export interface Contract {
  project_id: string;
  title: string;
  description: string;
  base_commit: string;
  snapshot_hash: string;
  environment: string;
  source: string;
  allowed_paths: string[];
  public_tests: string[];
  versions: Record<string, string>;
  verifier_id?: string | null;
  max_cost_cny: number;
  max_calls: number;
  max_seconds: number;
}
export interface Issue {
  id: string;
  project_id: string;
  contract: Contract;
}
export interface Run {
  id: string;
  issue_id: string;
  status: string;
  strategy: string;
  model_source: string;
  terminal_reason: string | null;
  spent: number;
  reserved: number;
  calls: number;
  created_at: number;
  started_at: number | null;
  ended_at: number | null;
  control: string | null;
  patch_hash: string | null;
  script: string;
}
export interface Agent {
  id: string;
  role: string;
  status: string;
  parent_id: string | null;
  key: string;
  summary: string;
  artifacts: string[];
}
export interface Artifact {
  id: string;
  kind: string;
  sha256: string;
  size: number;
  agent_id: string;
}
export interface Receipt {
  id: string;
  name: string;
  agent_id: string;
  status: string;
  arguments: unknown;
  result: unknown;
}
export interface Verification {
  id: string;
  passed: boolean;
  reason: string;
  patch_hash: string;
  environment_hash: string;
  verifier_hash: string;
  artifact_id: string;
}
export interface RunDetail extends Run {
  agents: Agent[];
  artifacts: Artifact[];
  receipts: Receipt[];
  verifications: Verification[];
  elapsed_seconds: number;
  scripted_test: boolean;
  model_calls: {
    id: string;
    status: string;
    actual: number | null;
    reserved: number;
    metadata_json: {
      error?: Record<string, unknown>;
      usage?: Record<string, unknown>;
    };
  }[];
}
export interface Trace {
  id: number;
  seq: number;
  kind: string;
  payload: Record<string, unknown>;
  created_at: number;
}
export interface Skill {
  id: string;
  name: string;
  version: number;
  content: string;
  active: boolean;
  sha256: string;
}
export interface Memory {
  id: string;
  project_id: string;
  version: number;
  status: string;
  entry: {
    content: string;
    source_artifacts: string[];
    applicable_versions: string[];
    invalidation_conditions: string;
  };
  validation: string[];
}
export interface Experiment {
  id: string;
  name: string;
  formal: boolean;
  config: { model_source: string; strategies: string[]; repetitions: number };
}
export interface Group {
  total: number;
  completed: number;
  succeeded: number;
  cost_cny: number;
  reserved_cny: number;
  latency_seconds: number[];
  failures: Record<string, number>;
}
export interface Report {
  scripted_test: boolean;
  formal_model_evidence: boolean;
  groups: Record<string, Group>;
  runs: Run[];
}
