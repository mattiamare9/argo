import { ShieldCheckIcon } from "lucide-react"
import { NavLink, Outlet } from "react-router"

import { cn } from "@/lib/utils"

// Le voci si aggiungono quando la feature corrispondente esiste davvero.
const NAV_ITEMS = [{ to: "/", label: "Dashboard" }]

export function AppLayout() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <span className="flex items-center gap-2 font-medium">
            <ShieldCheckIcon aria-hidden />
            Argo IAM
          </span>
          <nav className="flex gap-4 text-sm">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  cn(
                    "text-muted-foreground hover:text-foreground",
                    isActive && "text-foreground"
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
