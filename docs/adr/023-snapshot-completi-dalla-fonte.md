# ADR-023 – Snapshot completi dalla fonte, transizioni calcolate dal backend

**Stato:** Accettato
**Origine:** Fase 2 (2026-11-21). Modifica la specifica §5.1 punto 6 ("inviare le variazioni").

## Decisione

Il Sync Agent invia l'elenco completo dei dipendenti (`POST /api/v1/sync/snapshots`) quando il
contenuto della fonte cambia e comunque una volta l'ora. Il backend confronta lo snapshot con
l'anagrafica e calcola creazioni, aggiornamenti, disattivazioni e riattivazioni.

## Motivazione

- Con 10–30 dipendenti lo snapshot pesa pochi KB.
- Il backend resta l'unica fonte di verità sulle transizioni: se l'agent perde il suo stato
  locale, o una conferma di massa viene annullata, non si creano divergenze.
- Lo `snapshot_id` rende ogni invio idempotente.
- L'invio orario fa anche da segnale di vita dell'agent.

## Conseguenze

- Un dipendente assente dallo snapshot non viene mai disattivato: è solo contato
  (`missing_from_source`).
- Se una disattivazione di massa viene annullata e il file non viene corretto, il prossimo
  invio (al cambio del file o al segnale orario) la ripropone in attesa di conferma.
- L'agent conserva solo l'hash dell'ultimo invio accettato.
