"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { SidebarContext } from "@/hooks/useSidebar";
import "./globals.css";

// =============================================================================
// Sidebar Component — collapsible left navigation
// =============================================================================

function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const { user, role, signOut } = useAuth();
  const router = useRouter();

  async function handleSignOut() {
    await signOut();
    router.push("/login");
  }

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-surface-2 border-r border-border flex flex-col z-10 sidebar-transition ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center text-white font-bold text-sm shrink-0">
            AI
          </div>
          {!collapsed && (
            <div className="sidebar-label overflow-hidden">
              <div className="font-semibold text-sm text-text whitespace-nowrap">
                Support Agent
              </div>
              <div className="text-[11px] text-text-dim whitespace-nowrap">
                Dashboard
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 flex flex-col gap-1">
        <NavLink href="/" icon="📋" label="Tickets" collapsed={collapsed} />
        <NavLink
          href="/analytics"
          icon="📊"
          label="Analytics"
          collapsed={collapsed}
        />
        {role === "admin" && (
          <NavLink
            href="/admin"
            icon="🛡️"
            label="Admin Panel"
            collapsed={collapsed}
          />
        )}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="toggle-btn mx-2 mb-2 p-2 rounded-lg text-text-dim text-sm flex items-center justify-center"
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? "→" : "←"}
      </button>

      {/* User Info & Sign Out */}
      {!collapsed && user && (
        <div className="p-4 border-t border-border">
          <div className="text-[11px] text-text-dim truncate mb-1.5">
            {user.email}
          </div>
          <div className="flex items-center justify-between">
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full"
              style={{
                background:
                  role === "admin"
                    ? "rgba(138,92,246,0.15)"
                    : "rgba(99,102,241,0.15)",
                color: role === "admin" ? "#a78bfa" : "#818cf8",
              }}
            >
              {role}
            </span>
            <button
              onClick={handleSignOut}
              className="text-[11px] text-text-dim hover:text-red-400 transition-colors cursor-pointer"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      {!collapsed && (
        <div className="px-4 pb-3">
          <div className="text-[11px] text-text-dim">
            Powered by LangGraph + Gemini
          </div>
        </div>
      )}
    </aside>
  );
}

function NavLink({
  href,
  icon,
  label,
  collapsed,
}: {
  href: string;
  icon: string;
  label: string;
  collapsed: boolean;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-text-dim hover:text-text hover:bg-surface-3 transition-colors ${
        collapsed ? "justify-center" : ""
      }`}
      title={collapsed ? label : undefined}
    >
      <span>{icon}</span>
      {!collapsed && <span className="whitespace-nowrap">{label}</span>}
    </Link>
  );
}

// =============================================================================
// Root Layout
// =============================================================================

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  // Don't show sidebar on login page
  const isLoginPage = pathname === "/login";

  return (
    <html lang="en">
      <head>
        <title>Support Dashboard</title>
        <meta
          name="description"
          content="AI Customer Support Agent Dashboard"
        />
      </head>
      <body className="antialiased" suppressHydrationWarning>
        {isLoginPage ? (
          children
        ) : (
          <AuthGuard>
            <SidebarContext.Provider
              value={{ collapsed, toggle: () => setCollapsed(!collapsed) }}
            >
              <Sidebar
                collapsed={collapsed}
                onToggle={() => setCollapsed(!collapsed)}
              />
              <main
                className={`min-h-screen p-6 main-transition ${
                  collapsed ? "ml-16" : "ml-56"
                }`}
              >
                {children}
              </main>
            </SidebarContext.Provider>
          </AuthGuard>
        )}
      </body>
    </html>
  );
}

// =============================================================================
// Auth Guard — redirects to /login if not authenticated
// =============================================================================

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0f",
          color: "#94a3b8",
          fontSize: "0.875rem",
        }}
      >
        Loading...
      </div>
    );
  }

  return <>{children}</>;
}
