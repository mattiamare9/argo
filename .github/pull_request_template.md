## Cosa cambia

<!-- Una o due frasi. Se tocca una decisione architetturale: quale ADR. -->

## Verifiche

- [ ] `make ci` passa in locale (lo stesso controllo della CI)
- [ ] Nuove tabelle o colonne: migrazione Alembic generata e riletta
- [ ] Nuovo modulo backend: dipendenze dichiarate in `tests/test_module_boundaries.py`
- [ ] Interfaccia: provata a 1440 e 390 px (`cd e2e && npm run screens`)
- [ ] Nessun segreto nel diff; nuove variabili d'ambiente aggiunte ai file `.env*.example`
- [ ] Documentazione aggiornata (README, ARCHITECTURE, SECURITY, DEPLOYMENT dove serve)
