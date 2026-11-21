import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useLogout, useMe } from "@/features/auth/api"

/** Mostra i figli solo a chi ha un ruolo Argo; gli anonimi vanno al login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const me = useMe()
  const logout = useLogout()

  if (me.isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center p-8">
        <Skeleton className="h-10 w-64" />
      </div>
    )
  }

  if (me.isError || me.data.roles.length === 0) {
    return (
      <main className="flex min-h-screen flex-col justify-center gap-4 px-4 md:px-12">
        <h1 className="text-4xl font-bold tracking-[-0.03em] md:text-6xl">
          {me.isError ? "Argo non risponde" : "Non hai accesso ad Argo"}
        </h1>
        <p className="max-w-[60ch] text-base text-muted-foreground md:text-lg">
          {me.isError
            ? "Riprova tra qualche istante. Se continua, avvisa chi gestisce il sistema."
            : "Il tuo account esiste, ma non ha i permessi per la dashboard. Se pensi sia un errore, chiedi a chi gestisce il sistema."}
        </p>
        {!me.isError && (
          <div>
            <Button
              variant="outline"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              Esci
            </Button>
          </div>
        )}
      </main>
    )
  }

  return children
}
