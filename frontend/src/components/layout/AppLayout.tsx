import {
  AppWindowIcon,
  BookOpenTextIcon,
  FileSpreadsheetIcon,
  LayoutGridIcon,
  ListChecksIcon,
  UsersIcon,
} from "lucide-react"
import { NavLink, Outlet } from "react-router"

import { UserMenu } from "@/features/auth/UserMenu"
import { cn } from "@/lib/utils"

// Le voci si aggiungono quando la feature corrispondente esiste davvero.
const NAV_ITEMS = [
  { to: "/", label: "Panoramica", icon: LayoutGridIcon },
  { to: "/dipendenti", label: "Dipendenti", icon: UsersIcon },
  {
    to: "/sincronizzazione",
    label: "Sincronizzazione",
    icon: FileSpreadsheetIcon,
  },
  { to: "/operazioni", label: "Operazioni", icon: ListChecksIcon },
  { to: "/applicazioni", label: "Applicazioni", icon: AppWindowIcon },
  { to: "/registro", label: "Registro", icon: BookOpenTextIcon },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b bg-card px-4 py-3 md:sticky md:top-0 md:h-screen md:w-58 md:flex-col md:flex-nowrap md:items-stretch md:justify-start md:gap-6 md:border-r md:border-b-0 md:py-5">
        <span className="flex items-center gap-2.5 text-lg font-bold tracking-tight">
          <span
            aria-hidden
            className="grid size-7 place-items-center rounded-md bg-primary text-sm text-primary-foreground"
          >
            A
          </span>
          Argo
        </span>
        <nav
          aria-label="Principale"
          className="order-last -mx-4 flex w-[calc(100%+2rem)] gap-1 overflow-x-auto px-4 md:order-none md:mx-0 md:w-auto md:flex-col md:overflow-visible md:px-0"
        >
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-2.5 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
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
