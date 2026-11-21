import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useRuns, type Run } from "@/features/dashboard/api"
import { cn } from "@/lib/utils"

const dateTime = new Intl.DateTimeFormat("it-IT", {
  dateStyle: "short",
  timeStyle: "short",
})

const KIND: Record<Run["kind"], string> = {
  onboarding: "Nuovo accesso",
  offboarding: "Chiusura accessi",
  reactivation: "Riattivazione",
  profile_update: "Aggiornamento dati",
}

const STATUS: Record<Run["status"], string> = {
  completed: "Completata",
  in_progress: "In corso",
  partial: "Da completare",
}

export function OperationsPage() {
  const runs = useRuns(false)

  return (
    <div className="flex flex-col gap-6 px-4 py-8 md:px-12 md:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold tracking-[-0.03em]">Operazioni</h1>
        <p className="max-w-[60ch] text-muted-foreground">
          Cosa Argo ha fatto sugli accessi, passo per passo. Le operazioni da
          completare compaiono anche nella panoramica.
        </p>
      </div>
      {runs.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : runs.isError ? (
        <p role="alert" className="text-destructive">
          {runs.error.message}
        </p>
      ) : runs.data.length === 0 ? (
        <p className="text-muted-foreground">Ancora nessuna operazione.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quando</TableHead>
                <TableHead>Persona</TableHead>
                <TableHead>Operazione</TableHead>
                <TableHead>Stato</TableHead>
                <TableHead>Passi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.data.map((run) => {
                const done = run.steps.filter(
                  (s) => s.status === "SUCCESS"
                ).length
                return (
                  <TableRow key={run.id}>
                    <TableCell className="tabular-nums">
                      {dateTime.format(Date.parse(run.created_at))}
                    </TableCell>
                    <TableCell className="font-medium">
                      {run.employee_name}{" "}
                      <span className="font-normal text-muted-foreground">
                        · {run.employee_id}
                      </span>
                    </TableCell>
                    <TableCell>{KIND[run.kind]}</TableCell>
                    <TableCell
                      className={cn(
                        run.status === "partial" &&
                          "font-medium text-pending-foreground"
                      )}
                    >
                      {STATUS[run.status]}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {done} di {run.steps.length}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
