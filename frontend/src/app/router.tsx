import { createBrowserRouter } from "react-router"

import { AppLayout } from "@/components/layout/AppLayout"
import { RequireAuth } from "@/features/auth/RequireAuth"
import { DashboardPage } from "@/features/dashboard/DashboardPage"

export const router = createBrowserRouter([
  {
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [{ index: true, element: <DashboardPage /> }],
  },
])
