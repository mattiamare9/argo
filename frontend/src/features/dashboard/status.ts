import type { Station } from "@/features/dashboard/ServiceLine"
import type { Run, SyncOverview } from "@/features/dashboard/api"

// Oltre questo silenzio l'agent si considera fermo: invia comunque un segnale ogni ora.
const AGENT_SILENCE_MS = 2 * 60 * 60 * 1000

const time = new Intl.DateTimeFormat("it-IT", {
  hour: "2-digit",
  minute: "2-digit",
})

export type SystemInput = {
  apiDown: boolean
  dbDown: boolean
  workerStale?: boolean
  overview?: SyncOverview
  openRuns?: Run[]
  now: number
}

export type SystemStatus = {
  headline: string
  detail: string
  stations: Station[]
}

export function systemStatus({
  apiDown,
  dbDown,
  workerStale = false,
  overview,
  openRuns = [],
  now,
}: SystemInput): SystemStatus {
  const agent = overview?.agents[0]
  const lastSeen = agent?.last_seen_at ? Date.parse(agent.last_seen_at) : null
  const agentSilent = lastSeen !== null && now - lastSeen > AGENT_SILENCE_MS
  const partial = openRuns.filter((run) => run.status === "partial")
  const running = openRuns.length - partial.length

  const stations: Station[] = [
    {
      name: "Argo",
      state: apiDown ? "down" : "ok",
      detail: apiDown ? "non risponde" : "in linea",
    },
    {
      name: "Archivio",
      state: apiDown ? "unknown" : dbDown ? "down" : "ok",
      detail: apiDown
        ? "non verificabile"
        : dbDown
          ? "non risponde"
          : "raggiungibile",
    },
    {
      name: "File dipendenti",
      state:
        !agent || apiDown || dbDown
          ? "unknown"
          : agentSilent
            ? "down"
            : agent.last_error
              ? "pending"
              : "ok",
      detail: !agent
        ? "non ancora collegato"
        : agentSilent
          ? "nessun segnale"
          : agent.last_error
            ? "lettura sospesa"
            : `letto alle ${time.format(lastSeen ?? now)}`,
    },
    {
      name: "Operazioni",
      state:
        apiDown || dbDown
          ? "unknown"
          : workerStale
            ? "down"
            : partial.length
              ? "pending"
              : "ok",
      detail: workerStale
        ? "ferme"
        : partial.length
          ? `${partial.length} da completare`
          : running
            ? `${running} in corso`
            : "nessuna in coda",
    },
  ]

  if (apiDown) return { headline: "Argo non risponde", detail: RETRY, stations }
  if (dbDown)
    return { headline: "L'archivio non risponde", detail: RETRY, stations }
  if (workerStale) {
    return {
      headline: "Le operazioni sono ferme",
      detail:
        "Il programma che esegue le operazioni non dà segnali da qualche minuto: nuovi ingressi e uscite restano in coda. Avvisa chi gestisce il sistema.",
      stations,
    }
  }
  if (overview?.pending) {
    const n = overview.pending.deactivations.length
    return {
      headline: "Serve una tua conferma",
      detail: `Il file dei dipendenti chiede di disattivare ${n} persone insieme. Nessun accesso è stato toccato finché non decidi.`,
      stations,
    }
  }
  if (agentSilent) {
    return {
      headline: "Il file dei dipendenti non arriva",
      detail:
        "Il programma sul server aziendale non dà segnali da oltre due ore. Verifica che il server sia acceso.",
      stations,
    }
  }
  if (agent?.last_error) {
    return {
      headline: "La lettura del file è sospesa",
      detail: `${agent.last_error}. Correggi il file: Argo riprova da solo.`,
      stations,
    }
  }
  if (partial.length) {
    return {
      headline:
        partial.length === 1
          ? "Un'operazione è da completare"
          : `${partial.length} operazioni da completare`,
      detail:
        "Argo ha fatto il resto e ha bisogno di te per un passo. I dettagli sono qui sotto.",
      stations,
    }
  }
  return {
    headline: "Tutto in ordine",
    detail: agent
      ? "Nessuna azione richiesta"
      : "Nessuna azione richiesta · il file dei dipendenti non è ancora collegato",
    stations,
  }
}

const RETRY =
  "Riprovo da solo ogni 30 secondi. Se continua, avvisa chi gestisce il sistema."
