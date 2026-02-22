import type {
  TranscribeResponse,
  AnalyzeResponse,
  VisitRecord,
  ClinicalTrial,
  LiteratureResult,
  FeedbackItem,
  FeedbackAnalytics,
  AnalyticsSummary,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Transcribe ───────────────────────────────────────────────────────────────
export async function transcribeAudio(file: File): Promise<TranscribeResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/api/transcribe`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ─── Analyze ──────────────────────────────────────────────────────────────────
export async function analyzeTranscript(payload: {
  transcript: string;
  visit_date: string;
  visit_type: string;
  tags: string[];
}): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Visits ───────────────────────────────────────────────────────────────────
export async function getVisits(params?: {
  search?: string;
  tag?: string;
  sort?: string;
  page?: number;
}): Promise<VisitRecord[]> {
  const qs = new URLSearchParams();
  if (params?.search) qs.set("search", params.search);
  if (params?.tag) qs.set("tag", params.tag);
  if (params?.sort) qs.set("sort", params.sort);
  if (params?.page) qs.set("offset", String((params.page - 1) * 50));
  const data = await request<{ visits: VisitRecord[]; count: number }>(`/api/visits${qs.toString() ? `?${qs}` : ""}`);
  return data.visits ?? (data as unknown as VisitRecord[]);
}

export async function getVisit(id: number): Promise<VisitRecord> {
  return request<VisitRecord>(`/api/visits/${id}`);
}

export async function deleteVisit(id: number): Promise<void> {
  await request<void>(`/api/visits/${id}`, { method: "DELETE" });
}

// ─── PDF Export ───────────────────────────────────────────────────────────────
export async function exportPDF(visitId: number): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/api/export/${visitId}/pdf`);
  if (!res.ok) throw new Error(await res.text());
  return res.blob();
}

export function downloadPDF(blob: Blob, filename = "after-visit-summary.pdf") {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Trials & Literature ──────────────────────────────────────────────────────
export async function getTrials(visitId: number): Promise<ClinicalTrial[]> {
  return request<ClinicalTrial[]>(`/api/trials/${visitId}`);
}

export async function getLiterature(
  visitId: number,
  refresh = false
): Promise<LiteratureResult[]> {
  return request<LiteratureResult[]>(
    `/api/literature/${visitId}${refresh ? "?refresh=true" : ""}`
  );
}

// ─── Feedback ─────────────────────────────────────────────────────────────────
export async function submitFeedback(
  payload: Omit<FeedbackItem, "feedback_id" | "timestamp">
): Promise<{ feedback_id: number; message: string }> {
  return request("/api/feedback", { method: "POST", body: JSON.stringify(payload) });
}

export async function getFeedback(visitId: number): Promise<FeedbackItem[]> {
  return request<FeedbackItem[]>(`/api/feedback/${visitId}`);
}

export async function getFeedbackAnalytics(): Promise<FeedbackAnalytics> {
  return request<FeedbackAnalytics>("/api/feedback/analytics");
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export async function getAnalytics(): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>("/api/analytics");
}
