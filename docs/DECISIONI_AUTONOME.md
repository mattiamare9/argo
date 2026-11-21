# Decisioni prese in autonomia (2026-11-21, notte)

Lavoro svolto senza supervisione, su richiesta. Per ogni decisione: cosa ho scelto, perché, e
come cambiarla. Le decisioni che toccano l'architettura hanno anche un ADR.

## Da rivedere per prime

| # | Decisione | Perché | Se vuoi cambiarla |
|---|---|---|---|
| 1 | **Il primo collegamento del file crea gli account di tutti i dipendenti attivi e manda a ciascuno l'invito passkey.** | Coerente con "rendiamo la vita semplice": onboarding automatico. | Già pronto l'interruttore: `ARGO_SEND_INVITES=false` crea gli account senza inviti; al go-live `python -m app.cli send-invites` li manda a tutti. Decidi tu quale usare. |
| 2 | **Conferma delle disattivazioni di massa: sia `iam-admin` sia `iam-owner`.** | Dopo la consegna l'amministratore operativo è il titolare. | In `synchronization/router.py` usare solo `require_role("iam-admin")`. |
| 3 | **Soglia di massa: 3 o più disattivazioni nello stesso snapshot.** | Con 10–30 persone, 1–2 uscite insieme sono normali. | `ARGO_MASS_DEACTIVATION_THRESHOLD`. |
| 4 | **"Riprova" di un passo fallito: solo `iam-admin`. "Fatto" su un passo manuale: anche il titolare.** | Il retry è un'azione tecnica; il passo manuale lo fa chi gestisce l'app. | `provisioning/router.py`. |
| 5 | **Riattivazione = nuovo invito passkey** (oltre a riabilitare l'account). | Semplice e sicuro: se la vecchia passkey esiste ancora funziona comunque. | Handler `identity.provision`. |

## Identità e accesso

- **Username Keycloak = employee_id** (ADR-021): Keycloak 26 scarta gli attributi non dichiarati.
- **Login BFF senza libreria OIDC** (ADR-022): ~100 righe testate, nessuna dipendenza in più.
- **Login solo con passkey** (flusso `argo browser`: email → passkey), nessuna password.
  Recupero: l'admin rimuove la credenziale da Keycloak e rimanda l'invito.
- **Keycloak via `localhost` in sviluppo**: WebAuthn non accetta IP come dominio.
- **Scope `kc-admin-api`** sul service account: scoperto sul campo, Keycloak 26.8 lo richiede.

## Sincronizzazione

- **Snapshot completi invece di delta** (ADR-023): il backend calcola le transizioni, l'agent
  può perdere il suo stato senza danni.
- **Snapshot non valido = rifiutato per intero** (duplicati, email già di un altro). Meglio
  fermarsi che applicare metà file.
- **L'agent invia comunque ogni ora** come segnale di vita; oltre 2 ore di silenzio la
  dashboard lo segnala.
- **Profilo aggiornato solo per i dipendenti attivi**: chi è inattivo non ha accessi da aggiornare.

## Provisioning

- **Un job per passo**: un errore su un passo non annulla gli altri; l'offboarding resta
  "da completare" finché tutti i passi non sono riusciti o confermati a mano.
- **Offboarding chiude anche le sessioni della dashboard di Argo** del dipendente.
- **Disattivare chi non ha mai avuto un account = riuscito** (nulla da revocare).
- **~4 ore di tentativi** (10, backoff da 30 s a 1 h), poi FAILED visibile in dashboard.
- **Stato `MANUAL_PENDING`** aggiunto a quelli della specifica, per i SaaS senza API.

## Applicazioni (Fase 5, parziale)

- **Registro applicazioni con due connettori generici: manuale e SCIM 2.0.** Non conosco
  ancora le vostre app: SCIM è uno standard (RFC 7644), il manuale crea un'attività
  tracciata. Connettori per API specifiche si aggiungono quando sapremo quali app ci sono.
- **Segreti delle app cifrati (Fernet)** con chiave `ARGO_SECRETS_KEY` fuori dal DB; mai
  restituiti dall'API.
- **Registrare un'app non colora d'ambra il quadro**: un dipendente attivo mai toccato da
  Argo su quell'app si presume con accesso (chiave appesa). L'ambra resta per operazioni
  davvero in corso o non completate.
- **Profilo aggiornato: non propagato alle app** in questa iterazione (solo all'account aziendale).

## Interfaccia

- **Direzione "Quadro chiavi" con la palette "Linea Argo"** (scelta tua). La linea dei
  servizi diventa verticale su telefono, dove quattro etichette non stanno.
- **Dettagli tecnici degli errori visibili solo all'amministratore.**
- **Conferma di massa in due passi nella pagina** (non un modale): il primo clic mostra
  chi e quanti, il secondo esegue.
- **Tema di login "argo" per Keycloak**: estende il tema ufficiale cambiando solo colori,
  font e fondo (struttura e accessibilità restano di Keycloak). Le email di invito usano
  ancora il modello predefinito di Keycloak, in italiano.

## Produzione

- **Keycloak su un sottodominio separato** (`ARGO_AUTH_DOMAIN`); `/admin` bloccato da Caddy.
- **Migrazioni automatiche** a ogni deploy (servizio `migrate`).
- **Backup cifrati con openssl** (nessuna dipendenza nuova sulla VPS); restore in database
  separati per i test periodici.

## Secondo giro (dopo il tuo "continua")

- **Riverifica dei ruoli ogni 5 minuti** (correzione 6 del revisore). Se Keycloak è giù la
  sessione resta valida con i ruoli già noti: preferisco non chiudere fuori il titolare.
- **Chiavi dei Sync Agent gestite dalla dashboard** (crea, revoca), solo amministratore. La
  rotazione è "crea nuova → aggiorna il programma → revoca vecchia".
- **Pagina Registro** (audit, richiesta dalla specifica): filtri, ricerca, paginazione. I
  dettagli tecnici solo all'amministratore; i passi manuali in ambra "da fare a mano",
  non in rosso.
- **Interruttore inviti** `ARGO_SEND_INVITES` + comando `send-invites` (vedi decisione 1).
- **Ruolo DB `argo_app` in produzione**: API e worker non possono alterare l'audit né lo
  schema; solo le migrazioni usano il proprietario. Verificato su un Postgres usa-e-getta.
- **Tema di login Argo** in Keycloak (vedi Interfaccia).

## Revisione di sicurezza indipendente (fine sessione)

Un revisore senza il contesto della conversazione ha trovato 6 difetti; 5 corretti con test:

1. **Critico:** un job in ritardo poteva annullare un cambio più recente (es. invito ritentato
   dopo l'uscita → account riaperto). Ora ogni passo ricontrolla lo stato attuale.
2. **Importante:** "account non trovato" o "app non più gestita" risultavano un offboarding
   riuscito. Ora diventano un passo manuale da confermare; SCIM cerca per `externalId`.
3. **Importante:** due conferme della stessa disattivazione di massa potevano applicarla due
   volte. Ora la riga è bloccata e la seconda riceve 409.
4. Una ricerca utenti Keycloak in errore (realm sbagliato) ora è un errore, non "nessun utente".
5. Cambiare l'indirizzo SCIM cancella il token salvato.
6. Ruoli della dashboard: ora riverificati su Keycloak ogni 5 minuti (corretto al secondo giro).

## CI/CD (terzo giro)

- **Una CI unica** (`ci.yml`) senza filtri per percorso: tutto gira in ~3 minuti, ogni
  controllo può essere obbligatorio senza il problema dei check "in attesa per sempre".
- **Immagini costruite una volta in CI** (amd64 + arm64 per Oracle Ampere) e pubblicate su
  GHCR; il server scarica l'immagine del commit, non ricompila. Il bundle della dashboard
  si costruisce in modo nativo (`--platform=$BUILDPLATFORM`), solo il backend passa da QEMU.
- **Sicurezza bloccante**: gitleaks, pip-audit, npm audit (soglia high), Trivy su
  configurazione e immagini (CRITICAL con correzione disponibile). Il primo giro ha trovato
  due problemi veri, corretti: Caddy girava come root, OpenSSL dell'immagine base aveva CVE
  critiche (ora le immagini applicano gli aggiornamenti di sicurezza in build).
- **Deploy via SSH spento** finché la VPS non esiste (`DEPLOY_ENABLED`).
- **Email Microsoft 365 via OAuth2**: supportata da Keycloak 26.8.2 (verificato); la
  configurazione è pronta, servono i dati dall'amministratore Microsoft.
- Da residenceOS ho preso: concurrency, timeout, cache, controllo migrazioni, build unica
  su GHCR, PR template, `make ci`. Non ho preso: il deploy legato a Coolify.

## Risposte ricevute (2026-11-21 mattina)

| Tema | Risposta | Conseguenza |
|---|---|---|
| VPN | Nessuna informazione per ora | Resta fuori dal perimetro finché non serve |
| App custom (es. evacuationplan) | Non modificarle ora | Back-channel logout rimandato; l'offboarding chiude comunque l'account Keycloak |
| SaaS | Probabilmente non da toccare; l'azienda usa Microsoft | Connettore Microsoft Graph/Entra ID valutabile in seguito |
| PC aziendali | Strada più semplice per utente e titolare | Vedi sotto: proposta di non fare mTLS nel primo rilascio |
| Email | Domanda su Mailpit | Mailpit non spedisce; in produzione Microsoft 365 via OAuth2 (pronto) |
| VPS | Oracle (piano gratuito), sempre pronti a cambiare | Immagini multi-arch, deploy indipendente dal provider |
| Conservazione log | Qualche anno, da chiedere all'azienda | Nessuna cancellazione automatica per ora |
| Fonte dei dipendenti | Verrà scaricata da un sito web | Il Sync Agent ha già il punto di aggancio `SourceReader` |

## Rimandato, in attesa di te

| Tema | Cosa serve da te |
|---|---|
| Dispositivi aziendali (Fase 4) | Decidere se nel primo rilascio bastano le passkey (proposta) |
| Microsoft 365 | Accesso di un amministratore Entra ID per l'app di posta (e, se vorrai, per un connettore) |
| Fonte dei dipendenti dal sito web | URL, formato, autenticazione del sito |
| Conservazione dei log | Durata concordata con l'azienda |
| VPS Oracle | Creazione dell'account e della macchina (posso guidarti passo passo) |
