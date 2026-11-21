import { useState } from "react"

import { Button } from "@/components/ui/button"
import { useMe } from "@/features/auth/api"
import {
  useCancelSnapshot,
  useConfirmSnapshot,
  useResolveJob,
  useRetryJob,
  type Run,
  type Step,
  type SyncOverview,
} from "@/features/dashboard/api"

const RUN_KIND: Record<Run["kind"], string> = {
  onboarding: "Nuovo accesso",
  offboarding: "Chiusura accessi",
  reactivation: "Riattivazione",
  profile_update: "Aggiornamento dati",
}

const STEP_STATUS: Partial<Record<Step["status"], string>> = {
  FAILED: "non riuscito dopo vari tentativi",
  MANUAL_PENDING: "da fare a mano",
  RETRYING: "nuovo tentativo in arrivo",
  PENDING: "in coda",
  PROCESSING: "in corso",
}

type Props = {
  pending: SyncOverview["pending"]
  partialRuns: Run[]
}

/** Le sole cose che richiedono una persona. Se non c'è nulla, la sezione non esiste. */
export function AttentionList({ pending, partialRuns }: Props) {
  if (!pending && partialRuns.length === 0) return null
  return (
    <section aria-labelledby="da-seguire" className="flex flex-col gap-4">
      <h2 id="da-seguire" className="text-base font-semibold">
        Da seguire
      </h2>
      {pending && <PendingConfirmation pending={pending} />}
      {partialRuns.map((run) => (
        <PartialRun key={run.id} run={run} />
      ))}
    </section>
  )
}

function PendingConfirmation({
  pending,
}: {
  pending: NonNullable<SyncOverview["pending"]>
}) {
  const [armed, setArmed] = useState(false)
  const confirm = useConfirmSnapshot()
  const cancel = useCancelSnapshot()
  const n = pending.deactivations.length
  const busy = confirm.isPending || cancel.isPending
  const error = confirm.error ?? cancel.error

  return (
    <article className="flex flex-col gap-4 rounded-lg border border-pending bg-card p-5">
      <div className="flex flex-col gap-1">
        <h3 className="font-semibold">Disattivare {n} persone insieme?</h3>
        <p className="max-w-[65ch] text-sm text-muted-foreground">
          Il file dei dipendenti le segna come non attive. Confermando, Argo
          chiude i loro accessi. Se è un errore, annulla e correggi il file:
          altrimenti la richiesta si ripresenterà.
        </p>
      </div>
      <ul className="flex flex-wrap gap-2 text-sm">
        {pending.deactivations.map((person) => (
          <li
            key={person.employee_id}
            className="rounded-md bg-muted px-2.5 py-1"
          >
            {person.first_name} {person.last_name}{" "}
            <span className="text-muted-foreground">
              · {person.employee_id}
            </span>
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {error.message}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {armed ? (
          <>
            <Button
              variant="destructive"
              disabled={busy}
              onClick={() => confirm.mutate(pending.snapshot_id)}
            >
              Sì, chiudi gli accessi di {n} persone
            </Button>
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => setArmed(false)}
            >
              Torna indietro
            </Button>
          </>
        ) : (
          <>
            <Button disabled={busy} onClick={() => setArmed(true)}>
              Conferma la disattivazione
            </Button>
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => cancel.mutate(pending.snapshot_id)}
            >
              Annulla, non disattivare
            </Button>
          </>
        )}
      </div>
    </article>
  )
}

function PartialRun({ run }: { run: Run }) {
  const me = useMe()
  const retry = useRetryJob()
  const resolve = useResolveJob()
  const isAdmin = me.data?.roles.includes("iam-admin") ?? false
  const open = run.steps.filter((step) => step.status !== "SUCCESS")

  return (
    <article className="flex flex-col gap-3 rounded-lg border border-pending bg-card p-5">
      <h3 className="font-semibold">
        {RUN_KIND[run.kind]}: {run.employee_name}{" "}
        <span className="font-normal text-muted-foreground">
          · {run.employee_id}
        </span>
      </h3>
      <ul className="flex flex-col gap-3">
        {open.map((step) => (
          <li
            key={step.job_id}
            className="flex flex-col gap-2 border-t pt-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex min-w-0 flex-col">
              <span className="text-sm font-medium">{step.label}</span>
              <span className="text-sm text-pending-foreground">
                {STEP_STATUS[step.status]}
                {isAdmin && step.last_error && step.status !== "MANUAL_PENDING"
                  ? ` · ${step.last_error}`
                  : ""}
              </span>
              {step.status === "MANUAL_PENDING" && step.last_error && (
                <span className="text-sm">{step.last_error}</span>
              )}
            </div>
            {step.status === "FAILED" && isAdmin && (
              <Button
                variant="outline"
                size="sm"
                disabled={retry.isPending}
                onClick={() => retry.mutate(step.job_id)}
              >
                Riprova
              </Button>
            )}
            {step.status === "MANUAL_PENDING" && (
              <Button
                variant="outline"
                size="sm"
                disabled={resolve.isPending}
                onClick={() => resolve.mutate(step.job_id)}
              >
                Fatto
              </Button>
            )}
          </li>
        ))}
      </ul>
    </article>
  )
}
