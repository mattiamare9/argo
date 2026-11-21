---
version: 1
slug: "src-features-dashboard-dashboardpage-tsx"
primary_target: "src/features/dashboard/DashboardPage.tsx"
related_targets: ["src/components/layout/AppLayout.tsx"]
---

## Scope

Shell della dashboard di Argo e pagina Panoramica. Mode: Operate. Pubblico: titolare non tecnico (telefono e PC alla pari) e sviluppatore in fase di setup.

## Direction contract

THESIS: Gli accessi di ogni persona sono chiavi appese a un quadro di portineria: chiave appesa = accesso attivo, gancio vuoto = riconsegnata. Rifiuta la dashboard a card KPI con tabella "attività recenti".

OWN-WORLD: Fusione scelta dall'utente: struttura del Quadro chiavi, palette di Linea Argo. Fondo #f6f5f9 tinto di lilla, pannelli #fdfcff, inchiostro #1d1b26, lilla di linea #6e52a3 (marchio, chiavi attive, selezione), lilla tenue #ece7f5. Nessun grigio neutro: tutti i neutri sono tinti. Ambra #c98a12 solo per "in attesa/non riconsegnata", rosso #b8382c solo per guasti; mai come fondo di pagina. Hanken Grotesk, un solo carattere. Targhette con codice dipendente e chiavi etichettate con il nome dell'app.

STORY: Il titolare apre, legge in una frase se serve fare qualcosa, vede chi ha quali chiavi e quali non sono tornate, e conferma o va al dettaglio.

FIRST VIEWPORT: Barra laterale con marchio lilla e navigazione standard. In alto la riga dei servizi: sottile linea lilla con le fermate (file Excel, archivio, Keycloak, operazioni, email) e l'ora dell'ultima lettura; una fermata guasta si colora di rosso e la linea diventa tratteggiata. Sotto, la frase di stato a scala grande (es. "Tutte le chiavi sono al loro posto") con conteggi attivi/inattivi. Poi il quadro: griglia di targhette per persona con le chiavi per app; legenda fissa. Su telefono il quadro passa a una colonna; una conferma di disattivazione di massa occupa tutto lo schermo.

FORM: Quadro chiavi (candidato 1 della lista, carta IMPECCABLE'S PICK) con palette di Linea Argo (candidato 3, assegnato) per scelta dell'utente. seed:319b627680947fd3. Raise mantenuti: neutri tinti (Datamatics), una decisione per schermo su telefono (Feed verticale), stato che non ridipinge la base (Orienteering), un solo elemento possiede la pagina (Factory), frase di stato a scala manifesto (Tile tipografiche). Mossa firma: all'offboarding le chiavi si staccano dal gancio una alla volta mentre le revoche si confermano; quella che non torna resta in ambra.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Il quadro si popola solo con il modulo dipendenti (Fase 2): fino ad allora mostra uno stato vuoto onesto, nessun dato finto.
- Registro (audit) come "registro consegne chiavi": da progettare con la feature audit.
