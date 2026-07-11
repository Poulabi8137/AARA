import React from "react";

// Each page under (app) owns a single WorkspaceLayout call (sidebar/header/
// panel content differs per page). This layout must not wrap another
// WorkspaceLayout around it, or pages get a nested duplicate sidebar.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
