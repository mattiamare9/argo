import { createBrowserRouter } from "react-router"

import { AppLayout } from "@/components/layout/AppLayout"
import { DashboardPage } from "@/features/dashboard/DashboardPage"

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [{ index: true, element: <DashboardPage /> }],
  },
])
