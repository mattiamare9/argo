# ADR-022 – Login BFF senza libreria OIDC

**Stato:** Accettato
**Origine:** Fase 1 (2026-11-21)

## Decisione

Il backend esegue Authorization Code Flow + PKCE (S256) con httpx, senza librerie OIDC.
L'ID token è validato sui claims (`iss`, `aud`, `exp`, `nonce`) senza verificarne la firma.
La sessione è una riga in `user_sessions`; il browser riceve solo un token casuale opaco,
di cui il database conserva l'hash SHA-256. Nessun token Keycloak viene salvato.

## Motivazione

I token arrivano dal token endpoint tramite back-channel autenticato con il client secret:
OpenID Connect Core 1.0 §3.1.3.7 punto 6 consente in questo caso la validazione TLS al posto
della firma. Il flusso è circa 100 righe testate; una libreria (authlib) avrebbe aggiunto
middleware di sessione firmata e una dipendenza per lo stesso risultato.

## Conseguenze

- In produzione Keycloak deve essere raggiunto dal backend solo via HTTPS o rete interna.
- Il back-channel logout di Keycloak verso Argo (che richiede la verifica di firma di un
  logout token) non è implementato: la revoca delle sessioni dashboard passa da
  `sessions.revoke_for_subject`, chiamato dall'offboarding.
- Se servirà verificare JWT firmati (es. back-channel logout), si introduce allora una
  libreria JOSE, con un nuovo ADR.
