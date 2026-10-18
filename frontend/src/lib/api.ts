/**
 * IndexLens Backend API Client for Lovable UI
 * Connects the React/Vite/Next.js frontend directly to FastAPI.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export interface OverviewMetrics {
  total_spend_this_month: number;
  currency: string;
  active_subscriptions_count: number;
  upcoming_deadlines_count: number;
  vip_emails_count: number;
}

export interface ClassificationStats {
  total: number;
  deterministic_count: number;
  needs_llm_count: number;
  deterministic_rate: number;
  breakdown: Record<string, number>;
}

export interface OverviewResponse {
  metrics: OverviewMetrics;
  classification: ClassificationStats;
}

export interface Transaction {
  id: string;
  vendor: string;
  amount: number;
  currency: string;
  date: string;
  category: string;
  is_recurring: number;
  subject?: string;
  sender?: string;
  snippet?: string;
}

export interface SpendAnalytics {
  categories: Array<{ category: string; total: number; count: number }>;
  transactions: Transaction[];
  total_transactions: number;
  spend_trend?: Array<{ month: string; spend: number }>;
}

export interface Subscription {
  id?: number;
  vendor: string;
  cadence: string;
  last_amount: number;
  currency: string;
  last_charge_date?: string;
  next_expected_date: string;
  status: string;
  price_change_alert?: string | null;
}

export interface Newsletter {
  name: string;
  email: string;
  domain: string;
  last_subject: string;
  last_received: string;
  frequency: string;
  unsubscribe_url: string;
  volume_count: number;
}

export interface ImportantContactsResponse {
  vip_contacts: string[];
  recent_threads: Array<{
    id: string;
    sender: string;
    subject: string;
    date: string;
    snippet: string;
  }>;
}

export interface ScheduleResponse {
  meetings: Array<{
    id: string;
    title: string;
    datetime_start: string;
    location_or_link?: string;
    organizer?: string;
  }>;
  deadlines: Array<{
    id: string;
    description: string;
    due_date: string;
    urgency?: string;
    source_context?: string;
  }>;
}

export interface JobOpportunity {
  id: string;
  company: string;
  role: string;
  sender: string;
  date: string;
  status: string;
  snippet?: string;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export interface AskResponse {
  query: string;
  answer: string;
  sources: string[];
  model?: string;
}

export const api = {
  getOverview: () => request<OverviewResponse>("/stats/overview"),
  getSpend: () => request<SpendAnalytics>("/stats/spend"),
  getSubscriptions: () => request<Subscription[]>("/subscriptions"),
  getNewsletters: () => request<Newsletter[]>("/newsletters"),
  getImportantContacts: () => request<ImportantContactsResponse>("/contacts/important"),
  addImportantContact: (email: string, displayName = "", notes = "") =>
    request<{ status: string }>("/contacts/important", {
      method: "POST",
      body: JSON.stringify({ email, display_name: displayName, notes }),
    }),
  getSchedule: () => request<ScheduleResponse>("/schedule/upcoming"),
  getJobs: () => request<JobOpportunity[]>("/jobs"),
  syncInbox: (limit = 100, mock = false, extract = true) =>
    request<{ status: string; ingested_count: number; stats: ClassificationStats; extraction?: Record<string, number> }>("/inbox/sync", {
      method: "POST",
      body: JSON.stringify({ limit, mock, extract }),
    }),
  extractEntities: (limit = 100) =>
    request<{ status: string; results: Record<string, number> }>("/extract", {
      method: "POST",
      body: JSON.stringify({ limit }),
    }),
  askQuestion: (query: string) =>
    request<AskResponse>("/ask", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
  getEmailDetails: (emailId: string) => request<Record<string, unknown>>(`/emails/${emailId}`),
};
