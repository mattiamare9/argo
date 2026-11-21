# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Sviluppatore/integratore** (chi realizza e consegna il sistema): configura integrazioni, endpoint VPN, policy, chiavi dell'agent. Tecnico, usa la dashboard intensamente durante il setup.
- **Titolare dell'azienda cliente** (10–30 dipendenti): non tecnico. La sua attività ordinaria è aggiornare il file Excel dei dipendenti, non usare la dashboard. La apre solo quando serve: controllare che tutto funzioni, vedere offboarding rimasti a metà, confermare una disattivazione di massa, completare attività manuali tracciate. Usa telefono e PC con la stessa frequenza, spesso arrivando da un avviso.

## Product Purpose

Argo IAM centralizza identità e accessi di una piccola azienda e automatizza il ciclo di vita degli account: quando un dipendente passa da ATTIVO a INATTIVO nel file Excel, il sistema revoca da solo identità, sessioni, accessi ad applicazioni, VPN e SaaS, registra ogni esito e ritenta ciò che fallisce. Successo: il titolare modifica una cella e non deve fare altro; quando qualcosa non è andato a buon fine lo vede subito e capisce cosa fare.

## Positioning

Un IAM su misura per un'azienda piccola, guidato da un file che il titolare già usa, invece di una console IAM general-purpose da imparare. La dashboard esiste per dare fiducia e per le poche decisioni che richiedono un umano, non per l'operatività quotidiana.

## Operating Context

- Fonte dei dipendenti: file Excel condiviso su server aziendale (sostituibile in futuro), letto da un agent on-premise.
- Identity provider: Keycloak, login con passkey. Accesso alla dashboard con ruoli `iam-admin` (sviluppatore) e `iam-owner` (titolare).
- Momenti tipici del titolare: arriva da un'email di avviso ("disattivazione di massa in attesa di conferma", "offboarding parziale"), apre la dashboard, capisce lo stato, conferma o prende nota.
- Momenti tipici dello sviluppatore: sessioni di setup lunghe, form di configurazione, verifica di integrazioni, lettura di audit log ed errori.

## Capabilities and Constraints

- Oggi esiste solo la shell con lo stato del sistema (API, database). Pianificate: dipendenti, sincronizzazione, provisioning/offboarding, dispositivi, applicazioni, audit, impostazioni.
- Stato operazioni: PENDING, PROCESSING, SUCCESS, FAILED, RETRYING, MANUAL_PENDING. Offboarding COMPLETED solo se tutti i passi riusciti, altrimenti PARTIAL.
- Disattivazioni sopra soglia restano in attesa di conferma admin: nessuna revoca prima.
- Stack: React + TypeScript + Vite, shadcn/ui (base-nova, primitive Base UI), Tailwind v4, Lucide.
- Lingua: italiano ora; testi da tenere pronti per una futura traduzione in inglese (niente testo concatenato in modo intraducibile).
- Volumi piccoli: 10–30 dipendenti, decine di applicazioni al massimo.

## Brand Commitments

- Il brand visibile è solo il nome dell'app, **"Argo"**: niente nome dello sviluppatore, niente brand dell'azienda cliente.
- Nessun logo, colore o font preesistente: l'identità visiva definita per la dashboard diventa il brand di Argo.
- Da evitare (confermato): look da console tecnica (grigio, denso, gergo), tono allarmistico (rossi e avvisi quando va tutto bene), tono giocoso (illustrazioni e colori che tolgono serietà alle decisioni sugli accessi).

## Evidence on Hand

- Specifica architetturale e analisi: `../docs/ANALISI_ARCHITETTURALE.md`, `../docs/adr/`.
- Nessun dato reale di dipendenti, nessuno screenshot, nessun asset di brand. Non fabbricare nomi, numeri o loghi presentati come reali.

## Product Principles

1. **Il silenzio è il successo.** Se tutto funziona, la dashboard lo dice in una riga; l'attenzione va solo a ciò che richiede un umano.
2. **Mai ambiguità su un accesso.** Ogni persona e ogni operazione ha uno stato esplicito; "parziale" e "in attesa" non si nascondono mai dietro un verde.
3. **Le decisioni irreversibili sono esplicite.** Confermare una revoca di massa mostra chi, quanti e cosa succederà, prima del clic.
4. **Due pubblici, una sola verità.** Il titolare vede il riassunto comprensibile, lo sviluppatore il dettaglio tecnico: stessi dati, profondità diversa.

## Accessibility & Inclusion

- Uso su telefono e desktop con pari importanza: ogni flusso di decisione completo su schermo piccolo.
- Utente non tecnico: linguaggio semplice, nessun gergo IAM nelle viste del titolare; lo stato non si affida al solo colore.
