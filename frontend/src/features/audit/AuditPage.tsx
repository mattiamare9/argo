import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { SearchIcon } from "lucide-react"
import { useDeferredValue, useState } from "react"

import { useMe } from "@/features/auth/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { apiGet } from "@/lib/api"
import { cn } from "@/lib/utils"

type AuditEvent = {
  id: number
  occurred_at: string
  actor: string
  action: string
  outcome: "success" | "failure"
  target_type: string | null
  target_id: string | null
  details: Record<string, unknown>
}

type AuditPage = {
  items: AuditEvent[]
  total: number
  page: number
  page_size: number
}

type Filter = "all" | "success" | "failure"

const PAGE_SIZE = 25
const dateTime = new Intl.DateTimeFormat("it-IT", {
  dateStyle: "short",
  timeStyle: "medium",
})

const ACTIONS: Record<string, string> = {
  "auth.login": "Accesso",
  "auth.logout": "Uscita",
  "employee.created": "Nuovo dipendente",
  "employee.deactivated": "Dipendente uscito",
  "employee.reactivated": "Dipendente rientrato",
  "employee.updated": "Dati aggiornati",
  "sync.snapshot_applied": "Lettura del file applicata",
  "sync.snapshot_pending": "Conferma richiesta",
  "sync.snapshot_rejected": "File rifiutato",
  "sync.snapshot_confirmed": "Conferma data",
  "sync.snapshot_cancelled": "Conferma annullata",
  "sync.source_error": "Lettura del file sospesa",
  "identity.provision": "Account creato e invito inviato",
  "identity.disable": "Account disattivato",
  "identity.logout": "Sessioni chiuse",
  "dashboard.revoke_sessions": "Sessioni dashboard chiuse",
  "app.provision": "Account applicazione creato",
  "app.deprovision": "Account applicazione chiuso",
  "job.retry": "Nuovo tentativo",
  "job.manual_resolved": "Passo manuale confermato",
  "application.create": "Applicazione aggiunta",
  "application.update": "Applicazione modificata",
  "application.delete": "Applicazione eliminata",
}

function actorLabel(actor: string) {
  if (actor === "worker") return "Argo"
  if (actor === "cli") return "Riga di comando"
  if (actor.startsWith("agent:"))
    return `Programma di lettura (${actor.slice(6)})`
  if (actor.startsWith("user:")) return actor.slice(5)
  return actor
}

function detailsSummary(details: Record<string, unknown>) {
  return Object.entries(details)
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(" ")
}

function useAudit(search: string, filter: Filter, page: number) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(PAGE_SIZE),
  })
  if (search) params.set("search", search)
  if (filter !== "all") params.set("outcome", filter)
  return useQuery({
    queryKey: ["audit", search, filter, page],
    queryFn: () => apiGet<AuditPage>(`/api/audit?${params}`),
    placeholderData: keepPreviousData,
  })
}

export function AuditPage() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<Filter>("all")
  const [page, setPage] = useState(1)
  const deferredSearch = useDeferredValue(search.trim())
  const audit = useAudit(deferredSearch, filter, page)
  const isAdmin = useMe().data?.roles.includes("iam-admin") ?? false
  const pages = audit.data
    ? Math.max(1, Math.ceil(audit.data.total / PAGE_SIZE))
    : 1

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-12 md:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold tracking-[-0.03em]">Registro</h1>
        <p className="max-w-[60ch] text-muted-foreground">
          Tutto ciò che è successo agli accessi, in ordine. Non si può
          modificare né cancellare.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:w-80">
          <SearchIcon
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            aria-label="Cerca per chi, cosa o destinatario"
            placeholder="Cerca per chi, cosa o destinatario"
            className="pl-8"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </div>
        <ToggleGroup
          aria-label="Filtra per esito"
          variant="outline"
          value={[filter]}
          onValueChange={(value) => {
            if (value[0]) setFilter(value[0] as Filter)
            setPage(1)
          }}
        >
          <ToggleGroupItem value="all">Tutti</ToggleGroupItem>
          <ToggleGroupItem value="success">Riusciti</ToggleGroupItem>
          <ToggleGroupItem value="failure">Non riusciti</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {audit.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : audit.isError ? (
        <p role="alert" className="text-destructive">
          {audit.error.message}
        </p>
      ) : audit.data.items.length === 0 ? (
        <p className="text-muted-foreground">
          {deferredSearch || filter !== "all"
            ? "Nessun evento corrisponde alla ricerca."
            : "Nessun evento registrato."}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quando</TableHead>
                <TableHead>Chi</TableHead>
                <TableHead>Cosa</TableHead>
                <TableHead>Su</TableHead>
                <TableHead>Esito</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {audit.data.items.map((e) => {
                const summary = isAdmin ? detailsSummary(e.details) : ""
                return (
                  <TableRow key={e.id}>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {dateTime.format(Date.parse(e.occurred_at))}
                    </TableCell>
                    <TableCell>{actorLabel(e.actor)}</TableCell>
                    <TableCell>
                      <div className="font-medium">
                        {ACTIONS[e.action] ?? e.action}
                      </div>
                      {summary && (
                        <div
                          title={summary}
                          className="max-w-[40ch] truncate text-[13px] font-normal text-muted-foreground"
                        >
                          {summary}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {e.target_id ?? "—"}
                    </TableCell>
                    <TableCell
                      className={cn(
                        e.outcome === "failure" &&
                          (e.details.manual_required
                            ? "text-pending-foreground"
                            : "text-destructive")
                      )}
                    >
                      {e.outcome === "success"
                        ? "riuscito"
                        : e.details.manual_required
                          ? "da fare a mano"
                          : "non riuscito"}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {audit.data && pages > 1 && (
        <nav
          aria-label="Pagine"
          className="flex items-center justify-between gap-4 text-sm"
        >
          <span className="text-muted-foreground">
            {audit.data.total} eventi · pagina {page} di {pages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
            >
              Precedente
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage(page + 1)}
            >
              Successiva
            </Button>
          </div>
        </nav>
      )}
    </div>
  )
}
