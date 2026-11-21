# API di sincronizzazione (agent → backend)

Contratto tra il Sync Agent on-premise e il backend Argo. Indipendente dalla fonte (ADR-019):
nessun concetto di foglio, riga o colonna. Versione 1.

## Autenticazione

Ogni agent ha una chiave API, generata con `uv run python -m app.cli create-agent --name <nome>`
(mostrata una sola volta; in DB solo l'hash SHA-256).

```
Authorization: Bearer <chiave>
```

Chiave mancante, errata o revocata → `401`. Solo HTTPS in produzione.

## POST /api/v1/sync/snapshots

Elenco **completo** dei dipendenti letto dalla fonte (ADR-023). L'agent lo invia quando il
contenuto cambia e comunque almeno una volta ogni ora (segnale di vita).

```json
{
  "snapshot_id": "0b7c5f1e-3a0e-4c55-9a43-0f5e8e3f2a11",
  "source": "excel-hr",
  "read_at": "2026-11-21T10:42:00Z",
  "records": [
    {
      "employee_id": "E001",
      "email": "mario.rossi@azienda.it",
      "first_name": "Mario",
      "last_name": "Rossi",
      "status": "ACTIVE"
    }
  ]
}
```

- `snapshot_id`: UUID generato dall'agent. Reinviare lo stesso id è sicuro (idempotente).
- `status`: `ACTIVE` | `INACTIVE`. La traduzione dai valori della fonte (es. ATTIVO/INATTIVO)
  la fa l'agent.
- `records`: almeno 1 elemento, al massimo 1000. `employee_id` unici senza distinzione tra
  maiuscole e minuscole; `email` unica; tutti i campi obbligatori e non vuoti.

### Risposte

`200`:

```json
{
  "snapshot_id": "0b7c5f1e-…",
  "status": "applied",
  "summary": {
    "created": 1, "updated": 0, "deactivated": 0, "reactivated": 0,
    "unchanged": 24, "missing_from_source": 0
  }
}
```

`status`:
- `applied`: modifiche applicate.
- `pending_confirmation`: troppe disattivazioni insieme (ADR-020). Nulla è stato applicato;
  un amministratore conferma o annulla dalla dashboard. L'agent non deve fare nulla.
- `duplicate`: `snapshot_id` già ricevuto; restituisce l'esito originale.

`422`: snapshot non valido (duplicati, campi mancanti, stato sconosciuto). Nulla è applicato,
il motivo è nel corpo (`detail`). L'agent registra l'errore e riprova al prossimo cambio.

Regole lato backend:
- Un dipendente assente dallo snapshot **non** viene mai disattivato
  (`missing_from_source` lo conta soltanto).
- Solo `ACTIVE → INACTIVE` esplicito produce un offboarding.

## POST /api/v1/sync/agent-status

L'agent segnala che non può leggere la fonte (file assente, vuoto, corrotto, colonne mancanti,
dati non validi). La dashboard mostra la sincronizzazione come sospesa.

```json
{ "ok": false, "message": "Colonna obbligatoria mancante: status" }
```

`ok: true` azzera l'errore (lo fa anche ogni snapshot accettato). Risposta `204`.
