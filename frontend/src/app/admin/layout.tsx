"use client";

import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

/**
 * Admin layout — wraps all /admin/* pages.
 * Redirects to / if the user is not an admin.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { role, loading } = useAuth();
  const router = useRouter();

  if (loading) {
    return (
      <div className="text-text-dim text-sm py-12 text-center">
        Checking permissions...
      </div>
    );
  }

  if (role !== "admin") {
    router.push("/");
    return null;
  }

  return <>{children}</>;
}
