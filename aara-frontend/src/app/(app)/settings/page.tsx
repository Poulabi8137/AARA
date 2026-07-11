"use client";

import React from "react";
import { LogOut } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace/workspace-layout";
import { WorkspaceHeader } from "@/components/workspace/workspace-header";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <WorkspaceLayout header={<WorkspaceHeader title="Settings" />}>
      <div className="max-w-2xl space-y-6">
        <section className="rounded-xl border bg-card p-5 shadow-card">
          <h2 className="mb-4 text-base font-semibold text-foreground">
            Profile
          </h2>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Name</dt>
              <dd className="text-foreground">{user?.display_name || "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="text-foreground">{user?.email || "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Role</dt>
              <dd className="capitalize text-foreground">
                {user?.role || "—"}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border bg-card p-5 shadow-card">
          <h2 className="mb-1 text-base font-semibold text-foreground">
            Session
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">
            Sign out of AARA on this device.
          </p>
          <Button variant="outline" className="gap-1.5" onClick={handleLogout}>
            <LogOut className="size-4" />
            Log out
          </Button>
        </section>
      </div>
    </WorkspaceLayout>
  );
}
