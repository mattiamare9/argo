# ADR-004 – Sync Agent on-premise

**Stato:** Accettato
**Origine:** Specifica architetturale v1.0

## Decisione

Leggere la fonte da un servizio Python installato nella rete aziendale.

## Motivazione

Non esporre SMB; la VPS non accede alle risorse interne.

## Conseguenze

Solo connessioni in uscita verso il backend IAM.
