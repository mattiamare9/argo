import { createBrowserRouter } from "react-router"

import { AppLayout } from "@/components/layout/AppLayout"
import { ApplicationsPage } from "@/features/applications/ApplicationsPage"
import { AuditPage } from "@/features/audit/AuditPage"
import { RequireAuth } from "@/features/auth/RequireAuth"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { EmployeesPage } from "@/features/employees/EmployeesPage"
import { OperationsPage } from "@/features/provisioning/OperationsPage"
import { SyncPage } from "@/features/synchronization/SyncPage"

export const router = createBrowserRouter([
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "dipendenti", element: <EmployeesPage /> },
      { path: "sincronizzazione", element: <SyncPage /> },
      { path: "operazioni", element: <OperationsPage /> },
      { path: "applicazioni", element: <ApplicationsPage /> },
      { path: "registro", element: <AuditPage /> },
    ],
  },
])
