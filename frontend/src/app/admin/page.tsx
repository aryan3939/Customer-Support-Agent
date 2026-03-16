"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getAdminConversations,
  adminResolve,
  type ConversationSummary,
  type AdminFilters,
} from "@/lib/api";

// =============================================================================
// Admin Dashboard — Filterable conversation list
// =============================================================================

const STATUS_OPTIONS = ["", "new", "open", "resolved", "closed", "escalated"];
const PRIORITY_OPTIONS = ["", "low", "medium", "high", "urgent"];

export default function AdminDashboardPage() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [ticketId, setTicketId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const filters: AdminFilters = {
        limit,
        offset,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (status) filters.status = status;
      if (priority) filters.priority = priority;
      if (customerEmail) filters.customer_email = customerEmail;
      if (ticketId) filters.ticket_id = ticketId;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;

      const data = await getAdminConversations(filters);
      setConversations(data.conversations);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [status, priority, customerEmail, ticketId, dateFrom, dateTo, sortBy, sortOrder, limit, offset]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function handleResetFilters() {
    setStatus("");
    setPriority("");
    setCustomerEmail("");
    setTicketId("");
    setDateFrom("");
    setDateTo("");
    setOffset(0);
  }

  async function handleQuickResolve(convId: string) {
    try {
      await adminResolve(convId);
      fetchData();
    } catch {
      setError("Failed to resolve conversation");
    }
  }

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="max-w-[1200px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-text">🛡️ Admin Panel</h1>
          <p className="text-text-dim text-sm mt-1">
            Manage all conversations ({total} total)
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-xl bg-surface-2 border border-border p-4 mb-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold text-text-dim">Filters</span>
          <button
            onClick={handleResetFilters}
            className="text-[11px] text-accent hover:underline ml-auto"
          >
            Reset All
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {/* Status */}
          <FilterSelect
            label="Status"
            value={status}
            onChange={(v) => { setStatus(v); setOffset(0); }}
            options={STATUS_OPTIONS.map((s) => ({ value: s, label: s || "All" }))}
          />
          {/* Priority */}
          <FilterSelect
            label="Priority"
            value={priority}
            onChange={(v) => { setPriority(v); setOffset(0); }}
            options={PRIORITY_OPTIONS.map((p) => ({ value: p, label: p || "All" }))}
          />
          {/* Customer Email */}
          <div>
            <label className="text-[11px] text-text-dim block mb-1">Customer</label>
            <input
              type="text"
              value={customerEmail}
              onChange={(e) => { setCustomerEmail(e.target.value); setOffset(0); }}
              placeholder="email..."
              className="w-full px-2.5 py-1.5 rounded-lg bg-surface-3 border border-border text-text text-xs placeholder:text-text-dim focus:outline-none focus:border-accent"
            />
          </div>
          {/* Ticket ID */}
          <div>
            <label className="text-[11px] text-text-dim block mb-1">Ticket ID</label>
            <input
              type="text"
              value={ticketId}
              onChange={(e) => { setTicketId(e.target.value); setOffset(0); }}
              placeholder="UUID..."
              className="w-full px-2.5 py-1.5 rounded-lg bg-surface-3 border border-border text-text text-xs placeholder:text-text-dim focus:outline-none focus:border-accent"
            />
          </div>
          {/* Date From */}
          <div>
            <label className="text-[11px] text-text-dim block mb-1">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
              className="w-full px-2.5 py-1.5 rounded-lg bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
            />
          </div>
          {/* Date To */}
          <div>
            <label className="text-[11px] text-text-dim block mb-1">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
              className="w-full px-2.5 py-1.5 rounded-lg bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent"
            />
          </div>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-border/50">
          <span className="text-[11px] text-text-dim">Sort by:</span>
          <FilterSelect
            value={sortBy}
            onChange={setSortBy}
            options={[
              { value: "created_at", label: "Created" },
              { value: "updated_at", label: "Updated" },
              { value: "priority", label: "Priority" },
              { value: "status", label: "Status" },
            ]}
          />
          <button
            onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
            className="text-xs text-text-dim hover:text-text transition-colors px-2 py-1 rounded border border-border"
          >
            {sortOrder === "asc" ? "↑ Asc" : "↓ Desc"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="text-danger text-sm mb-4 p-3 rounded-lg bg-danger/10 border border-danger/20">
          {error}
        </div>
      )}

      {/* Conversation Table */}
      <div className="rounded-xl bg-surface-2 border border-border overflow-hidden">
        {loading ? (
          <div className="text-text-dim text-sm text-center py-12">
            Loading conversations...
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-text-dim text-sm text-center py-12">
            No conversations found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-dim text-xs">
                  <th className="text-left py-3 px-4 font-medium">Subject</th>
                  <th className="text-left py-3 px-3 font-medium">Customer</th>
                  <th className="text-left py-3 px-3 font-medium">Status</th>
                  <th className="text-left py-3 px-3 font-medium">Priority</th>
                  <th className="text-left py-3 px-3 font-medium">Msgs</th>
                  <th className="text-left py-3 px-3 font-medium">Created</th>
                  <th className="text-left py-3 px-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {conversations.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-border/50 hover:bg-surface-3/50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <Link
                        href={`/admin/conversations/${c.id}`}
                        className="text-text hover:text-accent transition-colors font-medium truncate block max-w-[250px]"
                      >
                        {c.subject}
                      </Link>
                      {c.latest_message_preview && (
                        <div className="text-[11px] text-text-dim truncate max-w-[250px] mt-0.5">
                          {c.latest_message_preview}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-xs text-text-dim">{c.customer_email}</span>
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="py-3 px-3">
                      <PriorityBadge priority={c.priority} />
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-xs text-text-dim">{c.message_count}</span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-xs text-text-dim">
                        {c.created_at
                          ? new Date(c.created_at).toLocaleDateString("en-IN", {
                              day: "2-digit",
                              month: "short",
                            })
                          : "—"}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5">
                        <Link
                          href={`/admin/conversations/${c.id}`}
                          className="px-2 py-1 rounded text-[11px] bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                        >
                          View
                        </Link>
                        {c.status !== "resolved" && c.status !== "closed" && (
                          <button
                            onClick={() => handleQuickResolve(c.id)}
                            className="px-2 py-1 rounded text-[11px] bg-success/10 text-success hover:bg-success/20 transition-colors"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <span className="text-xs text-text-dim">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1 text-xs rounded-lg border border-border text-text-dim hover:text-text disabled:opacity-30 transition-colors"
              >
                ← Prev
              </button>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1 text-xs rounded-lg border border-border text-text-dim hover:text-text disabled:opacity-30 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Helper Components
// =============================================================================

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      {label && (
        <label className="text-[11px] text-text-dim block mb-1">{label}</label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-2.5 py-1.5 rounded-lg bg-surface-3 border border-border text-text text-xs focus:outline-none focus:border-accent appearance-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
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
      className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
        styles[status] || "bg-surface-3 text-text-dim"
      }`}
    >
      {status}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const styles: Record<string, string> = {
    urgent: "text-danger font-semibold",
    high: "text-warning font-medium",
    medium: "text-text",
    low: "text-text-dim",
  };
  return (
    <span className={`text-xs ${styles[priority] || "text-text-dim"}`}>
      {priority}
    </span>
  );
}
