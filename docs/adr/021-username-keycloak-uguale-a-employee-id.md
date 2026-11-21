# ADR-021 – Username Keycloak uguale a employee_id

**Stato:** Accettato
**Origine:** Fase 1, verifica su Keycloak 26.8.2 (2026-11-21)

## Decisione

L'utente Keycloak di ogni dipendente ha `username` = `employee_id` (Keycloak lo normalizza
in minuscolo). Il login avviene per email, quindi l'utente non digita mai lo username.

## Motivazione

`employee_id` è la chiave stabile (specifica §5.2). Salvarlo come attributo personalizzato
richiederebbe di dichiararlo nel profilo utente di Keycloak: senza dichiarazione, verificato,
Keycloak 26 scarta gli attributi in silenzio. Lo username è già univoco, indicizzato e
ricercabile con `?username=<id>&exact=true` (senza distinzione tra maiuscole e minuscole).

## Conseguenze

- Due employee_id che differiscono solo per maiuscole/minuscole collidono: il Sync Agent
  li tratta come duplicati (validazione Fase 2).
- Cambi di email e nome si propagano con un PUT parziale; lo username non cambia mai.
