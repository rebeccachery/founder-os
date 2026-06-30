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

export interface Stats {
  investors: number;
  funding: number;
  grants: number;
  competitions: number;
  scout: number;
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
  score_total: number | null;
  rank_reason: string | null;
}

export const api = {
  stats: () => fetchApi<Stats>("/api/stats"),
  investors: () => fetchApi<Investor[]>("/api/investors"),
  funding: () => fetchApi<FundingOpportunity[]>("/api/funding"),
  grants: () => fetchApi<Grant[]>("/api/grants"),
  competitions: () => fetchApi<Competition[]>("/api/competitions"),
  scout: (minScore?: number) =>
    fetchApi<ScoutOpportunity[]>(
      minScore != null ? `/api/scout?min_score=${minScore}` : "/api/scout"
    ),
  deadlines: (days = 30) => fetchApi<Deadline[]>(`/api/deadlines?days=${days}`),
};
