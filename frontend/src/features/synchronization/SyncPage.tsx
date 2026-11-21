import { Skeleton } from "@/components/ui/skeleton"
import {
  useSyncOverview,
  type Snapshot,
  type SnapshotSummary,
} from "@/features/dashboard/api"
import { cn } from "@/lib/utils"

const dateTime = new Intl.DateTimeFormat("it-IT", {
  dateStyle: "short",
  timeStyle: "short",
})

const OUTCOME: Record<Snapshot["status"], string> = {
  applied: "Applicato",
  pending_confirmation: "In attesa di conferma",
  rejected: "Rifiutato",
  superseded: "Sostituito dal successivo",
  cancelled: "Annullato",
}

const SUMMARY_LABELS: [keyof SnapshotSummary, string, string][] = [
  ["created", "nuovo", "nuovi"],
  ["deactivated", "uscito", "usciti"],
  ["reactivated", "rientrato", "rientrati"],
  ["updated", "dati aggiornati", "dati aggiornati"],
  ["missing_from_source", "assente dal file", "assenti dal file"],
]

function describe(summary: SnapshotSummary): string {
  const parts = SUMMARY_LABELS.filter(([key]) => summary[key]).map(
    ([key, one, many]) => `${summary[key]} ${summary[key] === 1 ? one : many}`
  )
  return parts.length ? parts.join(" · ") : "nessun cambiamento"
}

export function SyncPage() {
  const overview = useSyncOverview()

  return (
    <div className="flex flex-col gap-8 px-4 py-8 md:px-12 md:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold tracking-[-0.03em]">
          Sincronizzazione
        </h1>
        <p className="max-w-[60ch] text-muted-foreground">
          Ogni lettura del file dei dipendenti e cosa ne è risultato. Un
          dipendente assente dal file non viene mai disattivato.
        </p>
      </div>

      {overview.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : overview.isError ? (
        <p role="alert" className="text-destructive">
          {overview.error.message}
        </p>
      ) : (
        <>
          <section aria-labelledby="agent" className="flex flex-col gap-3">
            <h2 id="agent" className="text-base font-semibold">
              Programma di lettura sul server aziendale
            </h2>
            {overview.data.agents.length === 0 ? (
              <p className="text-muted-foreground">
                Nessun programma collegato. Va installato sul server dove si
                trova il file (vedi la guida del Sync Agent).
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {overview.data.agents.map((agent) => (
                  <li
                    key={agent.name}
                    className="flex flex-col gap-1 rounded-lg border bg-card p-4"
                  >
                    <span className="font-medium">{agent.name}</span>
                    <span className="text-sm text-muted-foreground">
                      Ultimo contatto:{" "}
                      {agent.last_seen_at
                        ? dateTime.format(Date.parse(agent.last_seen_at))
                        : "mai"}
                    </span>
                    {agent.last_error && (
                      <span className="text-sm font-medium text-pending-foreground">
                        Lettura sospesa: {agent.last_error}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="letture" className="flex flex-col gap-3">
            <h2 id="letture" className="text-base font-semibold">
              Ultime letture
            </h2>
            {overview.data.recent.length === 0 ? (
              <p className="text-muted-foreground">Ancora nessuna lettura.</p>
            ) : (
              <ol className="flex flex-col divide-y rounded-lg border bg-card">
                {overview.data.recent.map((s) => (
                  <li
                    key={s.snapshot_id}
                    className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6"
                  >
                    <time
                      dateTime={s.received_at}
                      className="shrink-0 text-sm text-muted-foreground tabular-nums sm:w-36"
                    >
                      {dateTime.format(Date.parse(s.received_at))}
                    </time>
                    <span
                      className={cn(
                        "shrink-0 text-sm font-medium sm:w-56",
                        (s.status === "rejected" ||
                          s.status === "pending_confirmation") &&
                          "text-pending-foreground"
                      )}
                    >
                      {OUTCOME[s.status]}
                      {s.decided_by && s.status !== "superseded"
                        ? ` · ${s.decided_by}`
                        : ""}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {s.status === "rejected" ? s.detail : describe(s.summary)}
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </>
      )}
    </div>
  )
}
