"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getTicket,
  sendMessage,
  updateTicketStatus,
  type TicketDetail,
  type ActionResponse,
} from "@/lib/api";

// =============================================================================
// Action Type Metadata — icons and display labels for audit trail
// =============================================================================

const ACTION_META: Record<
  string,
  { icon: string; label: string; color: string }
> = {
  classify_ticket: {
    icon: "🏷️",
    label: "Classification",
    color: "text-info",
  },
  search_knowledge_base: {
    icon: "🔍",
    label: "KB Search",
    color: "text-accent",
  },
  generate_response: {
    icon: "💬",
    label: "Response Generated",
    color: "text-success",
  },
  validate_response: {
    icon: "✅",
    label: "Validation",
    color: "text-success",
  },
  escalate_ticket: {
    icon: "🚨",
    label: "Escalation",
    color: "text-danger",
  },
  finalize_response: {
    icon: "📤",
    label: "Finalized",
    color: "text-success",
  },
};

// =============================================================================
// Ticket Detail Page — Chat + Collapsible Sidebar
// =============================================================================

export default function TicketDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [msgInput, setMsgInput] = useState("");
  const [error, setError] = useState("");
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [isAgentMode, setIsAgentMode] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);

  const fetchTicket = useCallback(async () => {
    try {
      const data = await getTicket(id);
      setTicket(data);
    } catch {
      setError("Could not load ticket.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTicket();
  }, [fetchTicket]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!msgInput.trim()) return;
    setSending(true);
    setError("");
    try {
      await sendMessage(id, msgInput, isAgentMode ? "human_agent" : "customer");
      setMsgInput("");
      await fetchTicket();
    } catch {
      setError("Failed to send message");
    } finally {
      setSending(false);
    }
  }

  async function handleStatusUpdate(newStatus: string) {
    setStatusUpdating(true);
    setError("");
    try {
      await updateTicketStatus(id, newStatus);
      await fetchTicket();
    } catch {
      setError(`Failed to update status to ${newStatus}`);
    } finally {
      setStatusUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="text-text-dim text-sm py-12 text-center">
        Loading ticket...
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-3">❌</div>
        <div className="text-text-dim text-sm">
          {error || "Ticket not found"}
        </div>
        <Link
          href="/"
          className="text-accent text-sm mt-2 inline-block hover:underline"
        >
          ← Back to tickets
        </Link>
      </div>
    );
  }

  const isTerminal =
    ticket.status === "resolved" || ticket.status === "closed";

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col">
      {/* Breadcrumb + Controls */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-2 text-sm">
          <Link
            href="/"
            className="text-text-dim hover:text-accent transition-colors"
          >
            Tickets
          </Link>
          <span className="text-text-dim">/</span>
          <span className="text-text truncate max-w-md">{ticket.subject}</span>
        </div>

        {/* Right panel toggle */}
        <button
          onClick={() => setRightPanelOpen(!rightPanelOpen)}
          className="toggle-btn px-3 py-1.5 rounded-lg text-xs text-text-dim border border-border"
          title={rightPanelOpen ? "Hide details" : "Show details"}
        >
          {rightPanelOpen ? "Hide Panel ◀" : "Show Panel ▶"}
        </button>
      </div>

      <div className="flex gap-5 flex-1 min-h-0">
        {/* ================================================================= */}
        {/* Chat Area */}
        {/* ================================================================= */}
        <div className="flex-1 flex flex-col rounded-xl bg-surface-2 border border-border overflow-hidden min-h-0">
          {/* Chat Header */}
          <div className="p-4 border-b border-border flex items-center justify-between shrink-0">
            <div className="min-w-0">
              <h1 className="font-semibold text-text truncate">
                {ticket.subject}
              </h1>
              <div className="text-xs text-text-dim mt-0.5">
                {ticket.customer_email}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* Status Badge */}
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                  ticket.status === "resolved"
                    ? "bg-success/15 text-success"
                    : ticket.status === "closed"
                    ? "bg-text-dim/15 text-text-dim"
                    : ticket.status === "escalated"
                    ? "bg-danger/15 text-danger pulse-danger"
                    : "bg-info/15 text-info"
                }`}
              >
                {ticket.status}
              </span>

              {/* Status Action Buttons */}
              {!isTerminal && (
                <>
                  <button
                    onClick={() => handleStatusUpdate("resolved")}
                    disabled={statusUpdating}
                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-success/10 text-success hover:bg-success/20 transition-colors disabled:opacity-40"
                    title="Mark ticket as resolved"
                  >
                    ✓ Resolve
                  </button>
                  <button
                    onClick={() => handleStatusUpdate("closed")}
                    disabled={statusUpdating}
                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-text-dim/10 text-text-dim hover:bg-text-dim/20 transition-colors disabled:opacity-40"
                    title="Close ticket"
                  >
                    ✕ Close
                  </button>
                </>
              )}
              {ticket.status === "resolved" && (
                <button
                  onClick={() => handleStatusUpdate("open")}
                  disabled={statusUpdating}
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-warning/10 text-warning hover:bg-warning/20 transition-colors disabled:opacity-40"
                  title="Reopen ticket"
                >
                  ↩ Reopen
                </button>
              )}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 space-y-3 overflow-y-auto">
            {ticket.messages.map((m, i) => (
              <ChatBubble
                key={i}
                sender={m.sender_type}
                content={m.content}
                time={m.created_at}
              />
            ))}

            {ticket.messages.length === 0 && (
              <div className="text-text-dim text-sm text-center py-8">
                No messages yet
              </div>
            )}
          </div>

          {/* Input Area */}
          {!isTerminal && (
            <div className="border-t border-border shrink-0">
              {/* Agent Mode Toggle */}
              <div className="px-3 pt-2 flex items-center gap-3">
                <button
                  onClick={() => setIsAgentMode(false)}
                  className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
                    !isAgentMode
                      ? "bg-accent/15 text-accent font-medium"
                      : "text-text-dim hover:text-text"
                  }`}
                >
                  💬 Customer
                </button>
                <button
                  onClick={() => setIsAgentMode(true)}
                  className={`text-xs px-2.5 py-1 rounded-md transition-colors ${
                    isAgentMode
                      ? "bg-success/15 text-success font-medium"
                      : "text-text-dim hover:text-text"
                  }`}
                >
                  👤 Reply as Agent
                </button>
              </div>

              <form onSubmit={handleSend} className="p-3 flex gap-2">
                <input
                  value={msgInput}
                  onChange={(e) => setMsgInput(e.target.value)}
                  placeholder={
                    isAgentMode
                      ? "Reply as human agent..."
                      : "Type a follow-up message..."
                  }
                  className="flex-1 px-3 py-2 rounded-lg bg-surface-3 border border-border text-text text-sm placeholder:text-text-dim focus:outline-none focus:border-accent"
                />
                <button
                  type="submit"
                  disabled={sending || !msgInput.trim()}
                  className={`px-4 py-2 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-40 ${
                    isAgentMode
                      ? "bg-success hover:bg-success/80"
                      : "bg-accent hover:bg-accent-hover"
                  }`}
                >
                  {sending ? "..." : "Send"}
                </button>
              </form>

              {error && (
                <div className="px-4 pb-3 text-danger text-xs">{error}</div>
              )}
            </div>
          )}

          {isTerminal && (
            <div className="p-3 border-t border-border text-center text-text-dim text-xs">
              This ticket is {ticket.status}. Reopen to send messages.
            </div>
          )}
        </div>

        {/* ================================================================= */}
        {/* Right Panel — Classification + Audit Trail (Collapsible) */}
        {/* ================================================================= */}
        {rightPanelOpen && (
          <div className="w-80 shrink-0 space-y-4 overflow-y-auto min-h-0 panel-transition">
            {/* Classification Card */}
            <div className="rounded-xl bg-surface-2 border border-border p-4">
              <h2 className="font-semibold text-sm text-text mb-3">
                🧠 AI Classification
              </h2>
              <div className="space-y-2.5">
                <InfoRow
                  label="Intent"
                  value={ticket.ai_context?.intent}
                />
                <InfoRow label="Category" value={ticket.category} />
                <InfoRow
                  label="Priority"
                  value={ticket.priority}
                  color={
                    ticket.priority === "urgent"
                      ? "text-danger"
                      : ticket.priority === "high"
                      ? "text-warning"
                      : "text-text"
                  }
                />
                <InfoRow
                  label="Sentiment"
                  value={ticket.sentiment || ticket.ai_context?.sentiment}
                  color={
                    ticket.sentiment === "angry" ||
                    ticket.ai_context?.sentiment === "angry"
                      ? "text-danger"
                      : ticket.sentiment === "negative" ||
                        ticket.ai_context?.sentiment === "negative"
                      ? "text-warning"
                      : "text-text"
                  }
                />
                <InfoRow
                  label="Confidence"
                  value={
                    ticket.ai_context?.confidence
                      ? `${Math.round(ticket.ai_context.confidence * 100)}%`
                      : undefined
                  }
                />
              </div>
            </div>

            {/* Audit Trail */}
            {ticket.actions && ticket.actions.length > 0 && (
              <div className="rounded-xl bg-surface-2 border border-border p-4">
                <h2 className="font-semibold text-sm text-text mb-3">
                  📝 Audit Trail
                </h2>
                <div className="space-y-2.5">
                  {ticket.actions.map((a: ActionResponse, i: number) => (
                    <AuditCard key={i} action={a} />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Components
// =============================================================================

function AuditCard({ action }: { action: ActionResponse }) {
  const meta = ACTION_META[action.action_type] || {
    icon: "⚙️",
    label: action.action_type,
    color: "text-text",
  };

  const data = action.action_data || {};

  return (
    <div className="action-card text-xs p-3 rounded-lg bg-surface-3 border border-border/50">
      {/* Header */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-base">{meta.icon}</span>
        <span className={`font-semibold ${meta.color}`}>{meta.label}</span>
        {action.outcome && (
          <span
            className={`ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium ${
              action.outcome === "success"
                ? "bg-success/15 text-success"
                : action.outcome === "escalated"
                ? "bg-danger/15 text-danger"
                : action.outcome === "failure"
                ? "bg-danger/15 text-danger"
                : "bg-info/15 text-info"
            }`}
          >
            {action.outcome}
          </span>
        )}
      </div>

      {/* Reasoning */}
      {action.reasoning && (
        <div className="text-text-dim mb-1.5 leading-relaxed">
          {action.reasoning}
        </div>
      )}

      {/* Action Data Details */}
      {Object.keys(data).length > 0 && (
        <ActionDataDisplay type={action.action_type} data={data} />
      )}

      {/* Timestamp */}
      {action.created_at && (
        <div className="text-[10px] text-text-dim/60 mt-1.5">
          {new Date(action.created_at).toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </div>
      )}
    </div>
  );
}

function ActionDataDisplay({
  type,
  data,
}: {
  type: string;
  data: Record<string, unknown>;
}) {
  if (type === "classify_ticket") {
    return (
      <div className="grid grid-cols-2 gap-1 mt-1 p-2 rounded bg-surface-2/50">
        {!!data.intent && (
          <DataPill label="Intent" value={String(data.intent)} />
        )}
        {!!data.category && (
          <DataPill label="Category" value={String(data.category)} />
        )}
        {!!data.priority && (
          <DataPill
            label="Priority"
            value={String(data.priority)}
            color={
              data.priority === "urgent"
                ? "text-danger"
                : data.priority === "high"
                ? "text-warning"
                : undefined
            }
          />
        )}
        {!!data.sentiment && (
          <DataPill
            label="Sentiment"
            value={String(data.sentiment)}
            color={
              data.sentiment === "angry"
                ? "text-danger"
                : data.sentiment === "negative"
                ? "text-warning"
                : undefined
            }
          />
        )}
        {data.confidence !== undefined && (
          <DataPill
            label="Confidence"
            value={`${Math.round(Number(data.confidence) * 100)}%`}
          />
        )}
      </div>
    );
  }

  if (type === "search_knowledge_base") {
    const articles = (data.articles as string[]) || [];
    return (
      <div className="mt-1 p-2 rounded bg-surface-2/50">
        <div className="text-[10px] text-text-dim mb-1">
          Found {String(data.results_found || 0)} articles:
        </div>
        {articles.map((title, i) => (
          <div key={i} className="text-[10px] text-text flex items-start gap-1">
            <span className="text-accent">📄</span>
            <span>{title}</span>
          </div>
        ))}
      </div>
    );
  }

  if (type === "generate_response") {
    return (
      <div className="mt-1 p-2 rounded bg-surface-2/50">
        {data.kb_articles_used !== undefined && (
          <div className="text-[10px] text-text-dim">
            Used {String(data.kb_articles_used)} KB articles
          </div>
        )}
        {data.response_length !== undefined && (
          <div className="text-[10px] text-text-dim">
            Response: {String(data.response_length)} chars
          </div>
        )}
      </div>
    );
  }

  if (type === "validate_response") {
    return (
      <div className="mt-1 p-2 rounded bg-surface-2/50">
        {data.is_appropriate !== undefined && (
          <div className="text-[10px]">
            <span className="text-text-dim">Appropriate: </span>
            <span className={data.is_appropriate ? "text-success" : "text-danger"}>
              {data.is_appropriate ? "Yes ✓" : "No ✕"}
            </span>
          </div>
        )}
        {!!data.issues && (
          <div className="text-[10px] text-warning mt-0.5">
            Issues: {String(data.issues)}
          </div>
        )}
      </div>
    );
  }

  if (type === "escalate_ticket") {
    return (
      <div className="mt-1 p-2 rounded bg-danger/5 border border-danger/10">
        {!!data.reason && (
          <div className="text-[10px] text-danger">
            Reason: {String(data.reason)}
          </div>
        )}
      </div>
    );
  }

  // Generic fallback
  return (
    <div className="mt-1 p-2 rounded bg-surface-2/50">
      {Object.entries(data).map(([key, val]) => (
        <div key={key} className="text-[10px] text-text-dim">
          <span className="text-text">{key}:</span>{" "}
          {typeof val === "object" ? JSON.stringify(val) : String(val)}
        </div>
      ))}
    </div>
  );
}

function DataPill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="text-[10px]">
      <span className="text-text-dim">{label}: </span>
      <span className={`font-medium ${color || "text-text"}`}>{value}</span>
    </div>
  );
}

function ChatBubble({
  sender,
  content,
  time,
}: {
  sender: string;
  content: string;
  time?: string;
}) {
  const isCustomer = sender === "customer";
  const isHumanAgent = sender === "human_agent";
  return (
    <div className={`flex ${isCustomer ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isCustomer
            ? "bg-accent/20 text-text rounded-br-md"
            : isHumanAgent
            ? "bg-success/15 text-text rounded-bl-md border border-success/20"
            : "bg-surface-3 text-text rounded-bl-md"
        }`}
      >
        <div className="text-[11px] font-medium mb-1 opacity-60">
          {isCustomer
            ? "Customer"
            : isHumanAgent
            ? "👤 Human Agent"
            : "🤖 AI Agent"}
        </div>
        <div className="whitespace-pre-wrap">{content}</div>
        {time && (
          <div className="text-[10px] opacity-40 mt-1">
            {new Date(time).toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({
  label,
  value,
  color = "text-text",
}: {
  label: string;
  value: string | undefined | null;
  color?: string;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-xs text-text-dim">{label}</span>
      <span className={`text-xs font-medium ${color}`}>{value || "—"}</span>
    </div>
  );
}
