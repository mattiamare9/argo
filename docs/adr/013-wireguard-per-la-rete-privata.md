# ADR-013 – WireGuard per la rete privata

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

WireGuard per l'accesso alla rete privata.

## Motivazione

Leggero, open source, nessuna licenza.

## Conseguenze

Peer gestiti dal sistema IAM (Fase 5). Il container API non riceve privilegi di rete.
