import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiGet, apiPost } from "@/lib/api"

export type Health = {
  status: "ok" | "degraded"
  database: "ok" | "unreachable"
  worker?: "ok" | "stale" | "unknown"
}

// /api/health risponde 503 con un corpo valido quando il DB è giù: lo leggiamo comunque.
async function fetchHealth(): Promise<Health> {
  const response = await fetch("/api/health")
  if (response.status !== 200 && response.status !== 503) {
    throw new Error(`API non raggiungibile (HTTP ${response.status})`)
  }
  return response.json()
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })
}

export type SnapshotSummary = Partial<
  Record<
    | "created"
    | "updated"
    | "deactivated"
    | "reactivated"
    | "unchanged"
    | "missing_from_source",
    number
  >
>

export type Snapshot = {
  snapshot_id: string
  agent: string
  received_at: string
  status:
    "applied" | "pending_confirmation" | "rejected" | "superseded" | "cancelled"
  summary: SnapshotSummary
  detail: string | null
  decided_by: string | null
}

export type SyncOverview = {
  agents: {
    name: string
    last_seen_at: string | null
    last_error: string | null
    last_error_at: string | null
  }[]
  pending:
    | (Snapshot & {
        deactivations: {
          employee_id: string
          first_name: string
          last_name: string
        }[]
      })
    | null
  recent: Snapshot[]
}

export type Step = {
  job_id: string
  kind: string
  label: string
  status:
    | "PENDING"
    | "PROCESSING"
    | "SUCCESS"
    | "FAILED"
    | "RETRYING"
    | "MANUAL_PENDING"
  attempts: number
  last_error: string | null
  run_after: string
  resolved_by: string | null
}

export type Run = {
  id: string
  employee_id: string
  employee_name: string
  kind: "onboarding" | "offboarding" | "reactivation" | "profile_update"
  status: "in_progress" | "completed" | "partial"
  triggered_by: string
  created_at: string
  steps: Step[]
}

export type KeyState = "hung" | "returned" | "pending"

export type Plate = {
  employee_id: string
  first_name: string
  last_name: string
  status: "ACTIVE" | "INACTIVE"
  keys: { name: string; state: KeyState }[]
}

const LIVE = { refetchInterval: 15_000 }

export function useSyncOverview() {
  return useQuery({
    queryKey: ["sync", "overview"],
    queryFn: () => apiGet<SyncOverview>("/api/sync/overview"),
    ...LIVE,
  })
}

export function useRuns(onlyOpen: boolean) {
  return useQuery({
    queryKey: ["runs", { onlyOpen }],
    queryFn: () =>
      apiGet<Run[]>(`/api/provisioning/runs?only_open=${onlyOpen}`),
    ...LIVE,
  })
}

export function useBoard() {
  return useQuery({
    queryKey: ["board"],
    queryFn: () => apiGet<Plate[]>("/api/provisioning/board"),
    ...LIVE,
  })
}

/** Dopo ogni decisione tutto ciò che mostra lo stato va riletto. */
function useAction<T>(fn: (id: string) => Promise<T>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => client.invalidateQueries(),
  })
}

export const useConfirmSnapshot = () =>
  useAction((id) => apiPost<Snapshot>(`/api/sync/snapshots/${id}/confirm`))
export const useCancelSnapshot = () =>
  useAction((id) => apiPost<Snapshot>(`/api/sync/snapshots/${id}/cancel`))
export const useRetryJob = () =>
  useAction((id) => apiPost(`/api/provisioning/jobs/${id}/retry`))
export const useResolveJob = () =>
  useAction((id) => apiPost(`/api/provisioning/jobs/${id}/resolve`))
