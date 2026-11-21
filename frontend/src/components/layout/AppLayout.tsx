import { LayoutGridIcon } from "lucide-react"
import { NavLink, Outlet } from "react-router"

import { UserMenu } from "@/features/auth/UserMenu"
import { cn } from "@/lib/utils"

// Le voci si aggiungono quando la feature corrispondente esiste davvero.
const NAV_ITEMS = [{ to: "/", label: "Panoramica", icon: LayoutGridIcon }]

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 items-center justify-between gap-6 border-b bg-card px-4 py-3 md:w-58 md:flex-col md:items-stretch md:justify-start md:border-r md:border-b-0 md:py-5">
        <span className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span
            aria-hidden
            className="grid size-7 place-items-center rounded-md bg-primary text-sm text-primary-foreground"
          >
            A
          </span>
          Argo
        </span>
        <nav aria-label="Principale" className="flex gap-1 md:flex-col">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  isActive &&
                    "bg-secondary font-semibold text-secondary-foreground hover:bg-secondary"
                )
              }
            >
              <item.icon aria-hidden className="size-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <UserMenu />
      </aside>
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
    </div>
  )
}
