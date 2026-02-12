"use client";

import { useState, useEffect } from "react";
import { getDashboard, type DashboardMetrics } from "@/lib/api";

// =============================================================================
// Analytics Page — Metrics Dashboard
// =============================================================================

export default function Analytics() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboard()
      .then(setMetrics)
      .catch(() => setError("Could not load analytics. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-text-dim text-sm py-12 text-center">Loading analytics...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-3">📊</div>
        <div className="text-text-dim text-sm">{error}</div>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className="max-w-5xl">
      <h1 className="text-2xl font-bold text-text mb-6">Analytics</h1>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard label="Total Tickets" value={metrics.total_tickets} icon="📋" />
        <MetricCard label="Open" value={metrics.open_tickets} icon="🔵" color="text-info" />
        <MetricCard label="Resolved" value={metrics.resolved_tickets} icon="✅" color="text-success" />
        <MetricCard label="Escalated" value={metrics.escalated_tickets} icon="🔴" color="text-danger" />
      </div>

      {/* Rates */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <RateCard label="Resolution Rate" value={metrics.resolution_rate} icon="✅" />
        <RateCard label="Escalation Rate" value={metrics.escalation_rate} icon="🔴" />
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-3 gap-4">
        <BreakdownCard title="By Priority" data={metrics.priority_breakdown} />
        <BreakdownCard title="By Category" data={metrics.category_breakdown} />
        <BreakdownCard title="By Sentiment" data={metrics.sentiment_breakdown} />
      </div>
    </div>
  );
}

// =============================================================================
// Components
// =============================================================================

function MetricCard({
  label,
  value,
  icon,
  color = "text-text",
}: {
  label: string;
  value: number;
  icon: string;
  color?: string;
}) {
  return (
    <div className="p-4 rounded-xl bg-surface-2 border border-border">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-text-dim">{label}</span>
        <span className="text-lg">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

function RateCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: string;
}) {
  return (
    <div className="p-4 rounded-xl bg-surface-2 border border-border">
      <div className="text-sm text-text-dim mb-2">{icon} {label}</div>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-surface-3 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent rounded-full transition-all"
            style={{ width: `${Math.min(value, 100)}%` }}
          />
        </div>
        <span className="text-sm font-semibold text-text">{value}%</span>
      </div>
    </div>
  );
}

function BreakdownCard({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="p-4 rounded-xl bg-surface-2 border border-border">
        <h3 className="text-sm font-medium text-text mb-3">{title}</h3>
        <div className="text-xs text-text-dim">No data yet</div>
      </div>
    );
  }

  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="p-4 rounded-xl bg-surface-2 border border-border">
      <h3 className="text-sm font-medium text-text mb-3">{title}</h3>
      <div className="space-y-2">
        {Object.entries(data).map(([key, count]) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-text-dim capitalize">{key.replace(/_/g, " ")}</span>
              <span className="text-text">{count}</span>
            </div>
            <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent/60 rounded-full"
                style={{ width: `${total > 0 ? (count / total) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
