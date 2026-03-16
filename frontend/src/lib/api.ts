// =============================================================================
// API Client — typed wrappers for the FastAPI backend
// =============================================================================

import { getSupabaseBrowserClient } from "./supabase";

const BASE = "/api/v1";

// -----------------------------------------------------------------------------
// Types — matched to backend Pydantic schemas
// -----------------------------------------------------------------------------

export interface AgentInfo {
  id: string;
  name: string;
  is_ai: boolean;
}

export interface TicketSummary {
  id: string;
  customer_email: string;
  subject: string;
  status: string;
  priority: string;
  category: string | null;
  sentiment: string | null;
  assigned_to: AgentInfo | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface MessageResponse {
  id: string;
  ticket_id: string;
  sender_type: string;
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface ActionResponse {
  action_type: string;
  action_data: Record<string, unknown>;
  outcome: string | null;
  reasoning: string | null;
  created_at: string | null;
}

export interface TicketDetail extends TicketSummary {
  messages: MessageResponse[];
  actions: ActionResponse[];
  ai_context: {
    intent?: string;
    confidence?: number;
    sentiment?: string;
    kb_results_count?: number;
  };
}

export interface TicketListResponse {
  tickets: TicketSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateTicketResponse {
  id: string;
  status: string;
  priority: string;
  category: string | null;
  sentiment: string | null;
  assigned_to: AgentInfo;
  initial_response: string;
  escalated: boolean;
  escalation_reason: string | null;
  created_at: string;
}

export interface DashboardMetrics {
  total_tickets: number;
  open_tickets: number;
  resolved_tickets: number;
  escalated_tickets: number;
  resolution_rate: number;
  escalation_rate: number;
  priority_breakdown: Record<string, number>;
  category_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
}

// Admin types
export interface ConversationSummary extends TicketSummary {
  resolved_by: string | null;
  message_count: number;
  latest_message_preview: string | null;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminFilters {
  status?: string;
  priority?: string;
  category?: string;
  customer_email?: string;
  ticket_id?: string;
  date_from?: string;
  date_to?: string;
  resolved_by?: string;
  sort_by?: string;
  sort_order?: string;
  limit?: number;
  offset?: number;
}

// -----------------------------------------------------------------------------
// API Functions
// -----------------------------------------------------------------------------

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  // Get the current session token from Supabase
  const supabase = getSupabaseBrowserClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function getTickets(): Promise<TicketSummary[]> {
  const data = await apiFetch<TicketListResponse>("/tickets");
  return data.tickets;
}

export async function getTicket(id: string): Promise<TicketDetail> {
  return apiFetch<TicketDetail>(`/tickets/${id}`);
}

export async function createTicket(body: {
  customer_email: string;
  subject: string;
  message: string;
  channel?: string;
}): Promise<CreateTicketResponse> {
  return apiFetch<CreateTicketResponse>("/tickets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function sendMessage(
  ticketId: string,
  content: string,
  senderType: "customer" | "human_agent" = "customer"
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/tickets/${ticketId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content, sender_type: senderType }),
  });
}

export async function updateTicketStatus(
  ticketId: string,
  status: string
): Promise<TicketSummary> {
  return apiFetch<TicketSummary>(`/tickets/${ticketId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function resolveTicket(
  ticketId: string,
  resolvedBy: "customer" | "admin" = "customer"
): Promise<TicketSummary> {
  return apiFetch<TicketSummary>(`/tickets/${ticketId}/resolve`, {
    method: "PATCH",
    body: JSON.stringify({ resolved_by: resolvedBy }),
  });
}

export async function getDashboard(): Promise<DashboardMetrics> {
  return apiFetch<DashboardMetrics>("/analytics/dashboard");
}

// -----------------------------------------------------------------------------
// Admin API Functions
// -----------------------------------------------------------------------------

export async function getAdminConversations(
  filters: AdminFilters = {}
): Promise<ConversationListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return apiFetch<ConversationListResponse>(
    `/admin/conversations${query ? `?${query}` : ""}`
  );
}

export async function getAdminConversation(id: string): Promise<TicketDetail> {
  return apiFetch<TicketDetail>(`/admin/conversations/${id}`);
}

export async function adminReply(
  ticketId: string,
  content: string
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/admin/conversations/${ticketId}/reply`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function adminResolve(ticketId: string): Promise<TicketSummary> {
  return apiFetch<TicketSummary>(`/admin/conversations/${ticketId}/resolve`, {
    method: "PATCH",
  });
}
