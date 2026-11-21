# ADR-019 – API di sincronizzazione indipendente dalla fonte

**Stato:** Accettato
**Origine:** Analisi architetturale 2026-11-21 (docs/ANALISI_ARCHITETTURALE.md)

## Decisione

Il backend riceve record dipendente normalizzati con un campo `source`; nessun concetto di foglio, riga o colonna nell'API. Il Sync Agent legge tramite un protocollo `SourceReader`; Excel è la prima implementazione.

## Motivazione

La fonte può cambiare (CSV, gestionale, API) senza toccare il backend.

## Conseguenze

Il backend resta autorevole sulle transizioni e non si fida dell'agent.
