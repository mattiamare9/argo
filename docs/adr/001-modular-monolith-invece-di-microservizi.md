# ADR-001 – Modular monolith invece di microservizi

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Usare un backend modular monolith.

## Motivazione

Utenti e volumi (10–30) non giustificano la complessità dei microservizi.

## Conseguenze

Deploy semplice, poche risorse. Moduli indipendenti a livello logico (confini verificati da `tests/test_module_boundaries.py`), estraibili in futuro.
