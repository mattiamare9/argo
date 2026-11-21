import { Skeleton } from "@/components/ui/skeleton"
import { useHealth } from "@/features/dashboard/api"
import { KeySwatch, type KeyState } from "@/features/dashboard/KeySwatch"
import { ServiceLine, type Station } from "@/features/dashboard/ServiceLine"

type SystemStatus = "ok" | "api-down" | "db-down"

const HEADLINE: Record<SystemStatus, string> = {
  ok: "Tutto in ordine",
  "api-down": "Argo non risponde",
  "db-down": "L'archivio non risponde",
}

const RETRY_HINT =
  "Riprovo da solo ogni 30 secondi. Se continua, avvisa chi gestisce il sistema."

const LEGEND: { state: KeyState; label: string }[] = [
  { state: "hung", label: "Chiave appesa: accesso attivo" },
  { state: "returned", label: "Gancio vuoto: accesso riconsegnato" },
  { state: "pending", label: "Chiave in ambra: riconsegna non completata" },
]

const timeFormat = new Intl.DateTimeFormat("it-IT", {
  hour: "2-digit",
  minute: "2-digit",
})

export function DashboardPage() {
  const health = useHealth()
  const status: SystemStatus = health.isError
    ? "api-down"
    : health.data?.database === "unreachable"
      ? "db-down"
      : "ok"

  // Solo i servizi che esistono davvero: Excel, Keycloak e operazioni si aggiungono con i loro moduli.
  const stations: Station[] = [
    {
      name: "Argo",
      state: status === "api-down" ? "down" : "ok",
      detail: "in linea",
    },
    {
      name: "Archivio",
      state:
        status === "api-down"
          ? "unknown"
          : status === "db-down"
            ? "down"
            : "ok",
      detail: "raggiungibile",
    },
  ]

  return (
    <div className="flex flex-col">
      <section className="border-b bg-card px-4 pt-5 md:px-12">
        {health.isPending ? (
          <Skeleton className="mb-5 h-12 w-full" />
        ) : (
          <ServiceLine stations={stations} />
        )}
      </section>

      <section className="flex flex-col gap-3 px-4 pt-8 pb-8 md:px-12 md:pt-14">
        {health.isPending ? (
          <Skeleton className="h-14 w-full max-w-lg" />
        ) : (
          <>
            <h1 className="text-4xl font-bold tracking-[-0.03em] text-balance md:text-6xl">
              {HEADLINE[status]}
            </h1>
            <p className="max-w-[60ch] text-base text-muted-foreground md:text-lg">
              {status === "ok" ? (
                <>
                  Nessuna azione richiesta · controllato alle{" "}
                  <time>{timeFormat.format(health.dataUpdatedAt)}</time>
                </>
              ) : (
                RETRY_HINT
              )}
            </p>
          </>
        )}
      </section>

      <section aria-labelledby="quadro" className="px-4 pb-12 md:px-12">
        <h2 id="quadro" className="mb-4 text-base font-semibold">
          Quadro accessi
        </h2>
        {/* Il quadro vuoto: niente targhette finché il file dei dipendenti non è stato letto. */}
        <div className="flex flex-col gap-6 rounded-xl bg-muted p-6 shadow-[inset_0_2px_6px_rgb(74_54_120/0.08)] md:p-8">
          <div className="flex max-w-[60ch] flex-col gap-1.5">
            <p className="font-semibold">Il quadro è ancora vuoto</p>
            <p className="text-muted-foreground">
              Ogni dipendente comparirà qui con le chiavi delle applicazioni a
              cui ha accesso, alla prima lettura del file dei dipendenti.
            </p>
          </div>
          <ul
            aria-label="Legenda"
            className="flex flex-col gap-3 border-t border-input pt-5 text-sm md:flex-row md:gap-8"
          >
            {LEGEND.map((item) => (
              <li key={item.state} className="flex items-center gap-2.5">
                <KeySwatch state={item.state} />
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  )
}
