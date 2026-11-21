import { LogOutIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useLogout, useMe, type Role } from "@/features/auth/api"

const ROLE_LABEL: Record<Role, string> = {
  "iam-admin": "Amministratore",
  "iam-owner": "Titolare",
}

export function UserMenu() {
  const me = useMe()
  const logout = useLogout()
  if (!me.data) return null

  return (
    <div className="flex items-center gap-3 md:mt-auto md:flex-col md:items-stretch md:gap-2 md:border-t md:pt-4">
      <div className="hidden min-w-0 flex-col md:flex">
        <span className="truncate text-sm font-semibold">
          {me.data.display_name}
        </span>
        <span className="truncate text-[13px] text-muted-foreground">
          {me.data.roles.map((role) => ROLE_LABEL[role]).join(" · ")}
        </span>
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="md:justify-start"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        <LogOutIcon data-icon="inline-start" />
        Esci
      </Button>
    </div>
  )
}
