# ADR-017 – Adapter dentro il modulo proprietario

**Stato:** Accettato
**Origine:** Analisi architetturale 2026-11-21 (docs/ANALISI_ARCHITETTURALE.md)

## Decisione

Gli adapter vivono nel modulo che possiede la porta (es. `modules/identity/`), non in una cartella `infrastructure/` separata. Ogni modulo ha il suo router. Tra moduli si importa solo il package (`app.modules.x`), mai i file interni.

## Motivazione

Evita modifiche sparse su due cartelle e import incrociati.

## Conseguenze

Confini verificati da `backend/tests/test_module_boundaries.py`: ogni nuova dipendenza va dichiarata lì. Si discosta dalla struttura §10 della specifica.
