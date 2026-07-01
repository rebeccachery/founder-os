const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "dev-local-key";

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "X-API-Key": API_KEY },
    next: { revalidate: 60 },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${path}`);
  }
  return res.json();
}

export interface BriefingItem {
  title: string;
  category: string;
  due_at: string | null;
  priority_score: number;
  reason: string;
  url: string | null;
  source_id: number | null;
  status: string | null;
}

export interface BriefingConflict {
  summary: string;
  items: BriefingItem[];
  severity: string;
}

export interface ExecutiveBriefing {
  briefing_date: string;
  generated_at: string;
  priorities: BriefingItem[];
  conflicts: BriefingConflict[];
  follow_ups: BriefingItem[];
  deadlines: BriefingItem[];
  meetings: BriefingItem[];
  applications: BriefingItem[];
  summary_md: string | null;
}

export interface Stats {
  investors: number;
  funding: number;
  grants: number;
  competitions: number;
  scout: number;
  oss: number;
  social: number;
  deadlines_upcoming: number;
  contacts: number;
  new_items: number;
}

export interface Deadline {
  id: number;
  title: string;
  deadline_at: string;
  category: string;
  url: string | null;
  status: string;
}

export interface Investor {
  id: number;
  name: string;
  firm: string | null;
  stage: string | null;
  thesis: string | null;
  url: string | null;
  status: string;
}

export interface FundingOpportunity {
  id: number;
  name: string;
  organization: string | null;
  amount: string | null;
  stage: string | null;
  description: string | null;
  url: string | null;
  status: string;
}

export interface Grant {
  id: number;
  name: string;
  funder: string | null;
  amount: string | null;
  eligibility: string | null;
  url: string | null;
  deadline_at: string | null;
  status: string;
}

export interface Competition {
  id: number;
  name: string;
  organizer: string | null;
  prize: string | null;
  url: string | null;
  deadline_at: string | null;
  status: string;
}

export interface ScoutOpportunity {
  id: number;
  name: string;
  category: string;
  organization: string | null;
  amount: string | null;
  stage: string | null;
  description: string | null;
  url: string | null;
  deadline_at: string | null;
  status: string;
  source: string | null;
  score_total: number | null;
  rank_reason: string | null;
}

export interface SavedOpportunityInput {
  url?: string;
  name?: string;
  category?: string;
  deadline_at?: string;
  description?: string;
  source_tweet_url?: string;
  shared_by?: string;
}

export interface SavedOpportunity {
  id: number;
  name: string;
  category: string;
  url: string | null;
  deadline_at: string | null;
  status: string;
  source: string | null;
  score_total: number | null;
  rank_reason: string | null;
  description: string | null;
  created: boolean;
}

export interface OssResource {
  id: number;
  name: string;
  resource_type: string;
  organization: string | null;
  description: string | null;
  url: string | null;
  license: string | null;
  stars: number | null;
  last_updated_at: string | null;
  status: string;
  source: string | null;
  score_total: number | null;
  rank_reason: string | null;
}

export type OssView = "recent" | "reference" | "all";

export type SocialPostStatus = "draft" | "approved" | "posted" | "skipped" | "archived";

export interface SocialPost {
  id: number;
  content_type: string;
  platform: string | null;
  title: string | null;
  body: string;
  hook: string | null;
  source_refs: string | null;
  signal_score: number | null;
  status: SocialPostStatus;
  llm_model: string | null;
  generated_at: string;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

const apiHeaders = () => ({
  "X-API-Key": API_KEY,
  "Content-Type": "application/json",
});

export const api = {
  stats: () => fetchApi<Stats>("/api/stats"),
  investors: () => fetchApi<Investor[]>("/api/investors"),
  funding: () => fetchApi<FundingOpportunity[]>("/api/funding"),
  grants: () => fetchApi<Grant[]>("/api/grants"),
  competitions: () => fetchApi<Competition[]>("/api/competitions"),
  scout: (opts?: { minScore?: number; source?: "manual" | "agent" }) => {
    const params = new URLSearchParams();
    if (opts?.minScore != null) params.set("min_score", String(opts.minScore));
    if (opts?.source) params.set("source", opts.source);
    const qs = params.toString();
    return fetchApi<ScoutOpportunity[]>(`/api/scout${qs ? `?${qs}` : ""}`);
  },
  oss: (opts?: {
    view?: OssView;
    resourceType?: string;
    minScore?: number;
  }) => {
    const params = new URLSearchParams();
    if (opts?.view) params.set("view", opts.view);
    if (opts?.resourceType) params.set("resource_type", opts.resourceType);
    if (opts?.minScore != null) params.set("min_score", String(opts.minScore));
    const qs = params.toString();
    return fetchApi<OssResource[]>(`/api/oss${qs ? `?${qs}` : ""}`);
  },
  deadlines: (days = 30) => fetchApi<Deadline[]>(`/api/deadlines?days=${days}`),
  briefing: (date?: string) =>
    fetchApi<ExecutiveBriefing>(date ? `/api/briefing?date=${date}` : "/api/briefing"),
  social: (opts?: { status?: SocialPostStatus; contentType?: string }) => {
    const params = new URLSearchParams();
    if (opts?.status) params.set("status", opts.status);
    if (opts?.contentType) params.set("content_type", opts.contentType);
    const qs = params.toString();
    return fetchApi<SocialPost[]>(`/api/social${qs ? `?${qs}` : ""}`);
  },
};

export async function createSavedOpportunity(
  payload: SavedOpportunityInput
): Promise<SavedOpportunity> {
  const res = await fetch(`${API_URL}/api/opportunities/saved`, {
    method: "POST",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `API error: ${res.status}`;
    throw new Error(detail);
  }
  return res.json();
}

export async function updateSocialPost(
  id: number,
  payload: { status: SocialPostStatus; body?: string }
): Promise<SocialPost> {
  const res = await fetch(`${API_URL}/api/social/${id}`, {
    method: "PATCH",
    headers: apiHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} PATCH /api/social/${id}`);
  }
  return res.json();
}

export async function runSocialAgent(): Promise<{ message?: string }> {
  const res = await fetch(`${API_URL}/api/agents/run/social`, {
    method: "POST",
    headers: apiHeaders(),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} POST /api/agents/run/social`);
  }
  return res.json();
}
