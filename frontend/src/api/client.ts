import type { components } from "./sema";

export type Schemas = components["schemas"];
export type ChatResponse = Schemas["ChatResponse"];
export type DecoderOutput = Schemas["DecoderOutput"];
export type BrainActivity = Schemas["BrainActivity"];
export type BehaviorReadout = Schemas["BehaviorReadout"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Sunucuya bağlanılamadı. Uygulama çalışıyor mu? (uv run sinek)");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = "Geçersiz istek";
    } catch {
      // gövde JSON değil
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export function sendChat(message: string, signal?: AbortSignal): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
    ...(signal ? { signal } : {}),
  });
}

export type ScenariosResponse = Schemas["ScenariosResponse"];

export function getScenarios(signal?: AbortSignal): Promise<ScenariosResponse> {
  return request<ScenariosResponse>("/api/scenarios", signal ? { signal } : undefined);
}

// --- Laboratuvar ------------------------------------------------------------------------------

export type LabOptions = Schemas["LabOptions"];
export type ExperimentRequest = Schemas["ExperimentRequest"];
export type ExperimentResult = Schemas["ExperimentResult"];
export type JobStatus = Schemas["JobStatus"];
export type PathwayRequest = Schemas["PathwayRequest"];
export type PathwayResponse = Schemas["PathwayResponse"];
export type ExperimentReport = Schemas["ExperimentReport"];
export type ReplayResult = Schemas["ReplayResult"];
export type NeuronSelector = NonNullable<ExperimentRequest["silenced"]>[number];
export type CellTypeMatch = Schemas["CellTypeMatch"];
export type BehaviorComparison = Schemas["BehaviorComparison"];

export function getLabOptions(signal?: AbortSignal): Promise<LabOptions> {
  return request<LabOptions>("/api/lab/options", signal ? { signal } : undefined);
}

export function searchCellTypes(query: string, signal?: AbortSignal): Promise<CellTypeMatch[]> {
  const params = new URLSearchParams({ q: query });
  return request<CellTypeMatch[]>(`/api/neurons/search?${params}`, signal ? { signal } : undefined);
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export const startExperiment = (r: ExperimentRequest) => post<JobStatus>("/api/lab/run", r);
export const startPathways = (r: PathwayRequest) => post<JobStatus>("/api/lab/pathways", r);
export const startReport = (experiment: ExperimentRequest, title_tr: string | null) =>
  post<JobStatus>("/api/lab/report", { experiment, title_tr });
export const startReplay = (report: unknown) => post<JobStatus>("/api/lab/replay", report);

export function getJob(id: string, signal?: AbortSignal): Promise<JobStatus> {
  return request<JobStatus>(`/api/lab/jobs/${id}`, signal ? { signal } : undefined);
}

export type ExampleInfo = Schemas["ExampleInfo"];

export function listExamples(signal?: AbortSignal): Promise<ExampleInfo[]> {
  return request<ExampleInfo[]>("/api/lab/examples", signal ? { signal } : undefined);
}

export function getExample(name: string): Promise<ExperimentReport> {
  return request<ExperimentReport>(`/api/lab/examples/${encodeURIComponent(name)}`);
}
