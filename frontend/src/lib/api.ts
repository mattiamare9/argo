export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function redirectToLogin(): never {
  const next = window.location.pathname + window.location.search
  window.location.assign(`/api/auth/login?next=${encodeURIComponent(next)}`)
  // La pagina sta cambiando: blocca chi aspetta il risultato.
  throw new ApiError(401, "Accesso richiesto")
}

async function handle<T>(response: Response): Promise<T> {
  if (response.status === 401) redirectToLogin()
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(
      response.status,
      body?.detail ?? `Errore HTTP ${response.status}`
    )
  }
  return response.json()
}

export async function apiGet<T>(path: string): Promise<T> {
  return handle<T>(await fetch(path))
}

/** Le richieste che modificano dati portano l'header CSRF richiesto dal backend. */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return handle<T>(
    await fetch(path, {
      method: "POST",
      headers: { "X-Argo-CSRF": "1", "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  )
}
