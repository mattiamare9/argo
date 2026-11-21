import { useMutation, useQuery } from "@tanstack/react-query"

import { apiGet, apiPost } from "@/lib/api"

export type Role = "iam-admin" | "iam-owner"

export type Me = {
  username: string
  display_name: string
  email: string | null
  roles: Role[]
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<Me>("/api/auth/me"),
    staleTime: 5 * 60_000,
  })
}

export function useLogout() {
  return useMutation({
    mutationFn: () => apiPost<{ logout_url: string }>("/api/auth/logout"),
    onSuccess: ({ logout_url }) => window.location.assign(logout_url),
  })
}
