import { useQuery } from "@tanstack/react-query"

export type Health = {
  status: "ok" | "degraded"
  database: "ok" | "unreachable"
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
