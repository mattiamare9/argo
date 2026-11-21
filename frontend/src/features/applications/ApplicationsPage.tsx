import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState, type FormEvent } from "react"

import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { useMe } from "@/features/auth/api"
import { apiGet, apiPost, ApiError } from "@/lib/api"

type Connector = "manual" | "scim"

type Application = {
  id: string
  slug: string
  name: string
  connector: Connector
  config: { base_url?: string; notes?: string }
  has_secret: boolean
  enabled: boolean
}

const CONNECTOR_LABEL: Record<Connector, string> = {
  manual: "Manuale: Argo ti chiede di farlo e lo registra",
  scim: "Automatico (SCIM 2.0)",
}

async function send(method: "PATCH" | "DELETE", path: string, body?: unknown) {
  const response = await fetch(path, {
    method,
    headers: { "X-Argo-CSRF": "1", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ApiError(
      response.status,
      data?.detail ?? `Errore ${response.status}`
    )
  }
}

function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: () => apiGet<Application[]>("/api/applications"),
  })
}

export function ApplicationsPage() {
  const apps = useApplications()
  const me = useMe()
  const isAdmin = me.data?.roles.includes("iam-admin") ?? false

  return (
    <div className="flex flex-col gap-8 px-4 py-8 md:px-12 md:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold tracking-[-0.03em]">Applicazioni</h1>
        <p className="max-w-[60ch] text-muted-foreground">
          Le applicazioni di cui Argo gestisce gli account. Ognuna aggiunge una
          chiave al quadro accessi: quando un dipendente esce, Argo la chiude o
          ti chiede di farlo.
        </p>
      </div>

      {apps.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : apps.isError ? (
        <p role="alert" className="text-destructive">
          {apps.error.message}
        </p>
      ) : apps.data.length === 0 ? (
        <p className="text-muted-foreground">
          Nessuna applicazione collegata: oggi Argo gestisce solo l'account
          aziendale.
        </p>
      ) : (
        <ul className="flex flex-col divide-y rounded-lg border bg-card">
          {apps.data.map((app) => (
            <ApplicationRow key={app.id} app={app} isAdmin={isAdmin} />
          ))}
        </ul>
      )}

      {isAdmin && <NewApplicationForm />}
    </div>
  )
}

function ApplicationRow({
  app,
  isAdmin,
}: {
  app: Application
  isAdmin: boolean
}) {
  const client = useQueryClient()
  const toggle = useMutation({
    mutationFn: () =>
      send("PATCH", `/api/applications/${app.id}`, { enabled: !app.enabled }),
    onSettled: () => client.invalidateQueries(),
  })
  return (
    <li className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 flex-col">
        <span className="font-medium">
          {app.name}
          {!app.enabled && (
            <span className="font-normal text-muted-foreground">
              {" "}
              · sospesa
            </span>
          )}
        </span>
        <span className="text-sm text-muted-foreground">
          {CONNECTOR_LABEL[app.connector]}
          {app.connector === "scim" &&
            ` · ${app.config.base_url} · token ${app.has_secret ? "impostato" : "mancante"}`}
        </span>
        {toggle.error && (
          <span role="alert" className="text-sm text-destructive">
            {toggle.error.message}
          </span>
        )}
      </div>
      {isAdmin && (
        <Button
          variant="outline"
          size="sm"
          disabled={toggle.isPending}
          onClick={() => toggle.mutate()}
        >
          {app.enabled ? "Sospendi" : "Riattiva"}
        </Button>
      )}
    </li>
  )
}

function NewApplicationForm() {
  const client = useQueryClient()
  const [connector, setConnector] = useState<Connector>("manual")
  const create = useMutation({
    mutationFn: (body: unknown) => apiPost("/api/applications", body),
    onSuccess: () => client.invalidateQueries(),
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const text = (key: string) => String(form.get(key) ?? "").trim()
    create.mutate(
      {
        slug: text("slug"),
        name: text("name"),
        connector,
        config:
          connector === "scim"
            ? { base_url: text("base_url") }
            : text("notes")
              ? { notes: text("notes") }
              : {},
        ...(connector === "scim" && text("secret")
          ? { secret: text("secret") }
          : {}),
      },
      { onSuccess: () => (event.target as HTMLFormElement).reset() }
    )
  }

  return (
    <section
      aria-labelledby="nuova-app"
      className="flex max-w-xl flex-col gap-4"
    >
      <h2 id="nuova-app" className="text-base font-semibold">
        Aggiungi un'applicazione
      </h2>
      <form onSubmit={submit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="app-name">Nome</FieldLabel>
            <Input id="app-name" name="name" required maxLength={200} />
          </Field>
          <Field>
            <FieldLabel htmlFor="app-slug">Identificativo</FieldLabel>
            <Input
              id="app-slug"
              name="slug"
              required
              pattern="[a-z0-9-]+"
              maxLength={63}
            />
            <FieldDescription>
              Minuscole, numeri e trattini, es. fattura-facile.
            </FieldDescription>
          </Field>
          <Field>
            <FieldLabel>Come si chiudono gli account</FieldLabel>
            <ToggleGroup
              aria-label="Tipo di connettore"
              variant="outline"
              value={[connector]}
              onValueChange={(value) =>
                value[0] && setConnector(value[0] as Connector)
              }
            >
              <ToggleGroupItem value="manual">Manuale</ToggleGroupItem>
              <ToggleGroupItem value="scim">SCIM 2.0</ToggleGroupItem>
            </ToggleGroup>
          </Field>
          {connector === "scim" ? (
            <>
              <Field>
                <FieldLabel htmlFor="app-url">Indirizzo SCIM</FieldLabel>
                <Input
                  id="app-url"
                  name="base_url"
                  type="url"
                  required
                  placeholder="https://app.example.com/scim/v2"
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="app-secret">Token</FieldLabel>
                <Input
                  id="app-secret"
                  name="secret"
                  type="password"
                  autoComplete="off"
                />
                <FieldDescription>
                  Salvato cifrato, non verrà più mostrato.
                </FieldDescription>
              </Field>
            </>
          ) : (
            <Field>
              <FieldLabel htmlFor="app-notes">
                Istruzioni (facoltative)
              </FieldLabel>
              <Input id="app-notes" name="notes" maxLength={500} />
            </Field>
          )}
          {create.error && (
            <p role="alert" className="text-sm text-destructive">
              {create.error.message}
            </p>
          )}
          <div>
            <Button type="submit" disabled={create.isPending}>
              Aggiungi
            </Button>
          </div>
        </FieldGroup>
      </form>
    </section>
  )
}
