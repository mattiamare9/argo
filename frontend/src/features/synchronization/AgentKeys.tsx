import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { apiPost } from "@/lib/api"

/** Solo amministratore: nuova chiave per un programma di lettura, o revoca di una esistente. */
export function NewAgentKey() {
  const client = useQueryClient()
  const [created, setCreated] = useState<{ name: string; key: string } | null>(
    null
  )
  const create = useMutation({
    mutationFn: (name: string) =>
      apiPost<{ name: string; key: string }>("/api/sync/agents", { name }),
    onSuccess: (result) => {
      setCreated(result)
      client.invalidateQueries({ queryKey: ["sync"] })
    },
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = String(new FormData(event.currentTarget).get("name") ?? "")
    create.mutate(name.trim())
  }

  if (created) {
    return (
      <div className="flex flex-col gap-3 rounded-lg border border-pending bg-card p-4">
        <p className="font-semibold">Chiave per {created.name}</p>
        <p className="text-sm text-muted-foreground">
          Copiala ora nella configurazione del programma (variabile
          ARGO_AGENT_API_KEY): non verrà più mostrata.
        </p>
        <code className="rounded-md bg-muted px-3 py-2 text-sm break-all select-all">
          {created.key}
        </code>
        <div>
          <Button variant="outline" onClick={() => setCreated(null)}>
            Fatto, l'ho copiata
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="max-w-md">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="agent-name">
            Nuovo programma di lettura
          </FieldLabel>
          <Input
            id="agent-name"
            name="name"
            required
            pattern="[a-z0-9-]{1,60}"
            placeholder="excel-hr"
          />
          <FieldDescription>
            Per sostituire una chiave: creane una nuova, aggiorna il programma,
            poi revoca la vecchia.
          </FieldDescription>
        </Field>
        {create.error && (
          <p role="alert" className="text-sm text-destructive">
            {create.error.message}
          </p>
        )}
        <div>
          <Button type="submit" disabled={create.isPending}>
            Crea la chiave
          </Button>
        </div>
      </FieldGroup>
    </form>
  )
}

export function RevokeAgentButton({ name }: { name: string }) {
  const client = useQueryClient()
  const [armed, setArmed] = useState(false)
  const revoke = useMutation({
    mutationFn: () =>
      apiPost(`/api/sync/agents/${encodeURIComponent(name)}/revoke`),
    onSettled: () => client.invalidateQueries({ queryKey: ["sync"] }),
  })
  return armed ? (
    <div className="flex flex-wrap gap-2">
      <Button
        variant="destructive"
        size="sm"
        disabled={revoke.isPending}
        onClick={() => revoke.mutate()}
      >
        Sì, revoca la chiave
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setArmed(false)}>
        Annulla
      </Button>
    </div>
  ) : (
    <Button variant="outline" size="sm" onClick={() => setArmed(true)}>
      Revoca la chiave
    </Button>
  )
}
