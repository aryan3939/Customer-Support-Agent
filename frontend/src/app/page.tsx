"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { getTickets, createTicket, type TicketSummary } from "@/lib/api";

// =============================================================================
// Dashboard Page — Ticket List + Create
// =============================================================================

export default function Dashboard() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const fetchTickets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getTickets();
      setTickets(data);
    } catch {
      setError("Could not load tickets. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setCreating(true);
    setError("");

    const form = new FormData(e.currentTarget);
    try {
      await createTicket({
        customer_email: form.get("email") as string,
        subject: form.get("subject") as string,
        message: form.get("message") as string,
        channel: "web",
      });
      setShowForm(false);
      fetchTickets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text">Tickets</h1>
          <p className="text-text-dim text-sm mt-1">
            {tickets.length} ticket{tickets.length !== 1 && "s"} total
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors"
        >
          {showForm ? "Cancel" : "+ New Ticket"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error}
        </div>
      )}

      {/* Create Form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 p-5 rounded-xl bg-surface-2 border border-border space-y-4"
        >
          <h2 className="font-semibold text-text">Create New Ticket</h2>
          <div className="grid grid-cols-2 gap-4">
            <input
              name="email"
              type="email"
              placeholder="Customer email"
              required
              className="px-3 py-2 rounded-lg bg-surface-3 border border-border text-text text-sm placeholder:text-text-dim focus:outline-none focus:border-accent"
            />
            <input
              name="subject"
              placeholder="Subject (min 5 chars)"
              required
              minLength={5}
              className="px-3 py-2 rounded-lg bg-surface-3 border border-border text-text text-sm placeholder:text-text-dim focus:outline-none focus:border-accent"
            />
          </div>
          <textarea
            name="message"
            placeholder="Describe the issue... (min 10 chars)"
            rows={3}
            required
            minLength={10}
            className="w-full px-3 py-2 rounded-lg bg-surface-3 border border-border text-text text-sm placeholder:text-text-dim focus:outline-none focus:border-accent resize-none"
          />
          <button
            type="submit"
            disabled={creating}
            className="px-4 py-2 bg-accent hover:bg-accent-hover disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {creating ? "Creating... (AI is processing)" : "Create Ticket"}
          </button>
        </form>
      )}

      {/* Ticket List */}
      {loading ? (
        <div className="text-text-dim text-sm py-12 text-center">Loading tickets...</div>
      ) : tickets.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">📭</div>
          <div className="text-text-dim text-sm">No tickets yet. Create one to get started!</div>
        </div>
      ) : (
        <div className="space-y-2">
          {tickets.map((t) => (
            <TicketRow key={t.id} ticket={t} />
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Ticket Row Component
// =============================================================================

function TicketRow({ ticket }: { ticket: TicketSummary }) {
  return (
    <Link
      href={`/tickets/${ticket.id}`}
      className="block p-4 rounded-xl bg-surface-2 border border-border hover:border-accent/40 transition-colors group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm text-text group-hover:text-accent-hover transition-colors">
              {ticket.subject}
            </span>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
          <div className="text-xs text-text-dim truncate">
            {ticket.customer_email} · {ticket.category || "uncategorized"}
          </div>
        </div>
        <div className="text-xs text-text-dim whitespace-nowrap">
          {formatTime(ticket.created_at)}
        </div>
      </div>
    </Link>
  );
}

// =============================================================================
// Badges
// =============================================================================

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    open: "bg-info/15 text-info",
    in_progress: "bg-warning/15 text-warning",
    resolved: "bg-success/15 text-success",
    escalated: "bg-danger/15 text-danger",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${colors[status] || "bg-surface-3 text-text-dim"}`}>
      {status}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  if (!priority) return null;
  const colors: Record<string, string> = {
    urgent: "text-danger",
    high: "text-warning",
    medium: "text-info",
    low: "text-text-dim",
  };
  return (
    <span className={`text-[11px] font-medium ${colors[priority] || "text-text-dim"}`}>
      ● {priority}
    </span>
  );
}

function formatTime(iso: string) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
