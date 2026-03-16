"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  getAdminConversation,
  adminReply,
  adminResolve,
  type TicketDetail,
  type ActionResponse,
} from "@/lib/api";

// =============================================================================
// Admin Conversation Detail — Full thread + reply + resolve
// =============================================================================

export default function AdminConversationPage() {
  const params = useParams();
  const id = params.id as string;

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [replyContent, setReplyContent] = useState("");
  const [sending, setSending] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState("");

  const fetchTicket = useCallback(async () => {
    try {
      const data = await getAdminConversation(id);
      setTicket(data);
    } catch {
      setError("Could not load conversation.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTicket();
  }, [fetchTicket]);

  async function handleReply(e: React.FormEvent) {
    e.preventDefault();
    if (!replyContent.trim()) return;
    setSending(true);
    setError("");
    try {
      await adminReply(id, replyContent);
      setReplyContent("");
      await fetchTicket();
    } catch {
      setError("Failed to send reply");
    } finally {
      setSending(false);
    }
  }

  async function handleResolve() {
    setResolving(true);
    setError("");
    try {
      await adminResolve(id);
      await fetchTicket();
    } catch {
      setError("Failed to resolve conversation");
    } finally {
      setResolving(false);
    }
  }

  if (loading) {
    return (
      <div className="text-text-dim text-sm py-12 text-center">
        Loading conversation...
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-3">❌</div>
        <div className="text-text-dim text-sm">
          {error || "Conversation not found"}
        </div>
        <Link
          href="/admin"
          className="text-accent text-sm mt-2 inline-block hover:underline"
        >
          ← Back to admin
        </Link>
      </div>
    );
  }

  const isTerminal =
    ticket.status === "resolved" || ticket.status === "closed";

  return (
    <div className="max-w-[1100px] mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm">
          <Link
            href="/admin"
            className="text-text-dim hover:text-accent transition-colors"
          >
            Admin
          </Link>
          <span className="text-text-dim">/</span>
          <span className="text-text truncate max-w-md">{ticket.subject}</span>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={ticket.status} />
          {!isTerminal && (
            <button
              onClick={handleResolve}
              disabled={resolving}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-success/10 text-success hover:bg-success/20 transition-colors disabled:opacity-40"
            >
              {resolving ? "Resolving..." : "✓ Resolve"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="text-danger text-xs mb-3 p-2.5 rounded-lg bg-danger/10 border border-danger/20">
          {error}
        </div>
      )}

      <div className="flex gap-5">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col rounded-xl bg-surface-2 border border-border overflow-hidden" style={{ maxHeight: "calc(100vh - 8rem)" }}>
          {/* Header */}
          <div className="p-4 border-b border-border shrink-0">
            <h1 className="font-semibold text-text">{ticket.subject}</h1>
            <div className="text-xs text-text-dim mt-0.5 flex items-center gap-3">
              <span>{ticket.customer_email}</span>
              <span>•</span>
              <span>Priority: <strong className={ticket.priority === "urgent" ? "text-danger" : ticket.priority === "high" ? "text-warning" : ""}>{ticket.priority}</strong></span>
              {ticket.category && (
                <>
                  <span>•</span>
                  <span>{ticket.category}</span>
                </>
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

          {/* Reply Area */}
          {!isTerminal ? (
            <div className="border-t border-border shrink-0">
              <form onSubmit={handleReply} className="p-3 flex gap-2">
                <input
                  value={replyContent}
                  onChange={(e) => setReplyContent(e.target.value)}
                  placeholder="Reply as admin..."
                  className="flex-1 px-3 py-2 rounded-lg bg-surface-3 border border-border text-text text-sm placeholder:text-text-dim focus:outline-none focus:border-accent"
                />
                <button
                  type="submit"
                  disabled={sending || !replyContent.trim()}
                  className="px-4 py-2 bg-success text-white rounded-lg text-sm font-medium hover:bg-success/80 transition-colors disabled:opacity-40"
                >
                  {sending ? "..." : "Send"}
                </button>
              </form>
            </div>
          ) : (
            <div className="p-3 border-t border-border text-center text-text-dim text-xs">
              This conversation is {ticket.status}.
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="w-72 shrink-0 space-y-4 overflow-y-auto" style={{ maxHeight: "calc(100vh - 8rem)" }}>
          {/* AI Classification */}
          <div className="rounded-xl bg-surface-2 border border-border p-4">
            <h2 className="font-semibold text-sm text-text mb-3">
              🧠 AI Classification
            </h2>
            <div className="space-y-2">
              <InfoRow label="Intent" value={ticket.ai_context?.intent} />
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

          {/* Ticket Info */}
          <div className="rounded-xl bg-surface-2 border border-border p-4">
            <h2 className="font-semibold text-sm text-text mb-3">
              📋 Ticket Info
            </h2>
            <div className="space-y-2">
              <InfoRow label="ID" value={ticket.id.slice(0, 8) + "..."} />
              <InfoRow
                label="Created"
                value={
                  ticket.created_at
                    ? new Date(ticket.created_at).toLocaleDateString("en-IN")
                    : "—"
                }
              />
              <InfoRow
                label="Updated"
                value={
                  ticket.updated_at
                    ? new Date(ticket.updated_at).toLocaleDateString("en-IN")
                    : "—"
                }
              />
              {ticket.resolved_at && (
                <InfoRow
                  label="Resolved"
                  value={new Date(ticket.resolved_at).toLocaleDateString("en-IN")}
                />
              )}
            </div>
          </div>

          {/* Audit Trail */}
          {ticket.actions && ticket.actions.length > 0 && (
            <div className="rounded-xl bg-surface-2 border border-border p-4">
              <h2 className="font-semibold text-sm text-text mb-3">
                📝 Audit Trail
              </h2>
              <div className="space-y-2">
                {ticket.actions.map((a: ActionResponse, i: number) => (
                  <div
                    key={i}
                    className="text-xs p-2.5 rounded-lg bg-surface-3 border border-border/50"
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="font-medium text-text">
                        {a.action_type.replace(/_/g, " ")}
                      </span>
                      {a.outcome && (
                        <span
                          className={`ml-auto px-1.5 py-0.5 rounded text-[10px] ${
                            a.outcome === "success"
                              ? "bg-success/15 text-success"
                              : "bg-danger/15 text-danger"
                          }`}
                        >
                          {a.outcome}
                        </span>
                      )}
                    </div>
                    {a.reasoning && (
                      <div className="text-text-dim text-[11px] leading-relaxed">
                        {a.reasoning}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Helper Components
// =============================================================================

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
            ? "👤 Admin"
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

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    new: "bg-info/15 text-info",
    open: "bg-accent/15 text-accent",
    resolved: "bg-success/15 text-success",
    closed: "bg-text-dim/15 text-text-dim",
    escalated: "bg-danger/15 text-danger",
  };
  return (
    <span
      className={`px-2.5 py-1 rounded-full text-xs font-medium ${
        styles[status] || "bg-surface-3 text-text-dim"
      }`}
    >
      {status}
    </span>
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
