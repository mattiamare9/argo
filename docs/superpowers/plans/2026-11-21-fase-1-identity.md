# Fase 1 – Identity provider e accesso alla dashboard – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keycloak con login passkey, modulo `identity` (adapter Admin API), login BFF della dashboard con sessioni server-side revocabili e ruoli.

**Architecture:** Keycloak 26.8.2 nel profilo Compose `idp` con realm versionato. Il backend parla con Keycloak in due modi separati: `identity` usa l'Admin REST API con il service account `argo-backend`; `sessions` esegue l'Authorization Code Flow + PKCE come client confidenziale `argo-dashboard` e crea una sessione in `iam_db`. Il browser riceve solo un cookie opaco.

**Tech Stack:** FastAPI, SQLAlchemy async, httpx (nessuna nuova dipendenza runtime), Keycloak 26.8.2, Mailpit 1.34.0.

**Spec:** `docs/ANALISI_ARCHITETTURALE.md` (§2.2, §4, §5, §8.1), ADR-008, ADR-015, ADR-016.

## Global Constraints

- Nessun segreto nel repository o nel frontend; segreti da `deploy/.env` e `backend/.env`.
- Cookie di sessione `HttpOnly`, `SameSite=Lax`, `Secure` in produzione.
- Le richieste mutanti richiedono l'header `X-Argo-CSRF: 1` (nessun CORS abilitato, quindi un altro sito non può inviarlo).
- Ruoli: `iam-admin`, `iam-owner` (ruoli di realm Keycloak).
- Username Keycloak = `employee_id` (minuscolo, Keycloak normalizza). Verificato: gli attributi custom vengono scartati senza user profile dichiarato.
- Token Admin API: il client deve avere lo scope `kc-admin-api` (verificato su 26.8.2: senza, 401).
- Ogni login, logout e revoca va nell'audit.

## Fatti verificati su Keycloak 26.8.2 (2026-11-21)

- `POST /admin/realms/argo/users` → 201; duplicato → 409.
- `GET /admin/realms/argo/users?username=<id>&exact=true` (case-insensitive).
- `PUT /admin/realms/argo/users/{id}` con body parziale → 204, gli altri campi restano; id inesistente → 404.
- `POST /admin/realms/argo/users/{id}/logout` → 204.
- `PUT /admin/realms/argo/users/{id}/execute-actions-email?lifespan=<s>` con `["webauthn-register-passwordless"]` → 204, email in Mailpit.
- `GET /admin/realms/argo/roles/{name}` + `POST /users/{id}/role-mappings/realm` → 204 (service account con `view-realm`).
- Import realm: `start-dev --import-realm`, file `data/import/<realm>-realm.json`, saltato se il realm esiste; placeholder `${ENV}` sostituiti.

## Review Focus

1. Callback con `state` diverso dal cookie (login CSRF) → 400, nessuna sessione.
2. Sessione scaduta per inattività o revocata → 401 anche se il cookie è presente.
3. Utente autenticato senza ruoli `iam-*` → 403 su ogni API protetta (un dipendente qualunque non entra in dashboard).
4. Keycloak irraggiungibile durante il callback → 502 con messaggio chiaro, nessuna sessione parziale.
5. POST senza header CSRF → 403.

---

### Task 1: Keycloak e realm in Compose (fatto durante la verifica)

**Files:** `deploy/compose.yaml`, `deploy/keycloak/argo-realm.json`, `deploy/.env.example`
- [x] Profilo `idp`: keycloak 26.8.2 (`start-dev --import-realm`, heap ≤512m, health su 9000), mailpit 1.34.0.
- [x] Realm `argo`: ruoli, client `argo-dashboard` (PKCE S256) e `argo-backend` (service account + `kc-admin-api`), flusso `argo browser` (username → passkey), SMTP verso mailpit.

### Task 2: Modulo `identity` – porta + adapter Keycloak

**Files:** create `backend/app/modules/identity/{__init__,ports,keycloak_adapter,service}.py`, test `backend/tests/identity/test_keycloak_adapter.py`; modify `app/core/config.py`, `tests/test_module_boundaries.py`.

**Interfaces – Produces:**
- `IdentityUser(employee_id: str, email: str, first_name: str, last_name: str)` (dataclass frozen)
- `class IdentityProvider(Protocol)`: `async ensure_user(user) -> None`, `async set_enabled(employee_id, enabled: bool) -> None`, `async logout(employee_id) -> None`, `async send_enrollment(employee_id) -> None`, `async grant_role(employee_id, role: str) -> None`
- `IdentityError(Exception)`, `UserNotFound(IdentityError)`
- `KeycloakIdentityProvider(base_url, realm, client_id, client_secret, http: httpx.AsyncClient)`

Tests (httpx.MockTransport): token richiesto una volta e riusato fino a scadenza; `ensure_user` crea (POST) se assente, aggiorna (PUT parziale) se presente; `set_enabled` su utente assente → `UserNotFound`; 5xx → `IdentityError`; `send_enrollment` invia `["webauthn-register-passwordless"]`. Test di integrazione `@pytest.mark.keycloak` contro il realm reale, saltati se `ARGO_TEST_KEYCLOAK_URL` non è impostato.

### Task 3: Modulo `sessions` – BFF OIDC

**Files:** create `backend/app/modules/sessions/{__init__,models,repository,oidc,service,router,dependencies}.py`, migrazione `0002_sessions.py`, test `backend/tests/sessions/`.

**Interfaces – Produces:**
- `CurrentUser(subject: str, username: str, display_name: str, email: str | None, roles: frozenset[str])`
- dipendenze FastAPI: `current_user`, `require_role(*roles)`, `require_csrf`
- `async revoke_for_subject(session, subject: str) -> int`
- Router: `GET /api/auth/login?next=`, `GET /api/auth/callback`, `POST /api/auth/logout` → `{"logout_url": str}`, `GET /api/auth/me` → `CurrentUser`

Tabelle: `login_attempts(state PK, nonce, code_verifier, next_path, created_at)` (scadenza 10 min); `sessions(id, token_hash UNIQUE, subject, username, display_name, email, roles JSONB, created_at, last_seen_at, expires_at, revoked_at)`. Cookie = token casuale (`secrets.token_urlsafe(32)`), in DB solo SHA-256. Inattività 30 min, assoluta 10 h (allineate al realm). `next` accetta solo percorsi relativi che iniziano con `/` e non con `//`.

Tests: i cinque punti di Review Focus, più login completo con token endpoint mockato, `/me` 200, logout → 401 dopo, audit scritto per login/logout.

### Task 4: CLI bootstrap admin

**Files:** create `backend/app/cli.py`; test `backend/tests/test_cli.py`.
- `uv run python -m app.cli bootstrap-admin --employee-id ADMIN --email ... --first-name ... --last-name ...` → `ensure_user`, `grant_role("iam-admin")`, `send_enrollment`. Test con provider finto.

### Task 5: Frontend auth

**Files:** create `frontend/src/features/auth/{api.ts,RequireAuth.tsx,UserMenu.tsx}`; modify `app/router.tsx`, `components/layout/AppLayout.tsx`, `features/dashboard/api.ts`.
- `useMe()`; 401 → `window.location.assign("/api/auth/login?next=" + path)`; 403 → schermata "Non hai accesso" con logout.
- Nel layout: nome utente e azione "Esci" (POST con `X-Argo-CSRF: 1`, poi redirect a `logout_url`).
- Verifica: build, lint, screenshot della pagina 403 e del layout autenticato (sessione creata via test helper).

### Task 6: Documentazione

ADR-021 (username = employee_id), ADR-022 (BFF senza libreria OIDC, validazione claims da back-channel), DEVELOPMENT.md (profilo idp, bootstrap admin, Mailpit), SECURITY.md (sessioni, CSRF, limiti: niente back-channel logout ancora).
