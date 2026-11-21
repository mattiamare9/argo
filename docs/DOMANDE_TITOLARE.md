# Domande per il titolare

Cosa chiedere all'azienda, perché serve e cosa cambia in Argo con la risposta.
Le prime cinque bloccano la messa in produzione; le altre si possono chiedere dopo.

## Per andare in produzione

### 1. Da dove scarichiamo l'elenco dei dipendenti?
**Chiedi:** il sito da cui si scarica il file (o l'Excel attuale), come ci si accede
(utente/password? Lo scarica una persona o può farlo un programma?), ogni quanto è
aggiornato, e un esempio del file con dati finti.
**Perché:** Argo decide chi ha accesso guardando quell'elenco. Il programma che lo legge è
pronto per un Excel; per un sito serve sapere come entrarci e com'è fatto il file.
**Cosa cambia:** scriviamo il "lettore" per quella fonte (il resto di Argo non cambia).

### 2. Chi è il codice univoco di ogni dipendente?
**Chiedi:** nel file c'è una colonna con un codice (matricola) che non cambia mai, nemmeno
se cambiano nome o email? Lo stato "attivo / non attivo" com'è scritto?
**Perché:** Argo riconosce le persone da quel codice. Usare nome o email porterebbe a
disattivare la persona sbagliata quando cambiano.
**Cosa cambia:** la configurazione delle colonne e dei valori di stato.

### 3. Chi gestisce Microsoft 365 in azienda?
**Chiedi:** chi è l'amministratore di Microsoft 365 / Entra ID (interno o un fornitore) e
se può darci 30 minuti per configurare l'invio delle email.
**Perché:** gli inviti per creare la passkey partono dalla casella aziendale. Microsoft
non accetta più la sola password per i programmi: l'amministratore deve autorizzare Argo.
**Cosa cambia:** senza, gli inviti non arrivano ai dipendenti.

### 4. Da quale indirizzo devono arrivare le email di Argo?
**Chiedi:** una casella tipo `accessi@azienda.it` (nuova o esistente) e due nomi di
dominio, es. `argo.azienda.it` (la dashboard) e `accesso.azienda.it` (la pagina di login).
**Perché:** i dipendenti devono riconoscere l'email come aziendale, e i due indirizzi web
servono per i certificati HTTPS.
**Cosa cambia:** configurazione della produzione (`.env.prod`).

### 5. Si parte con tutti insieme o a gruppi?
**Chiedi:** al primo collegamento Argo crea l'account di tutti i dipendenti attivi e manda
a ciascuno l'invito. Va bene tutti lo stesso giorno, o prima una prova con poche persone?
**Perché:** è il momento in cui tutti ricevono un'email nuova; meglio che siano avvisati.
**Cosa cambia:** l'interruttore `ARGO_SEND_INVITES` (inviti sospesi fino al giorno scelto).

## Dopo, con calma

### 6. Quanto tempo conservare il registro degli accessi?
**Chiedi:** per quanti anni tenere la storia di accessi, uscite e operazioni (serve
all'azienda, al consulente privacy o per obblighi di legge?).
**Perché:** il registro contiene dati personali (GDPR): va tenuto il giusto, non per sempre.
**Cosa cambia:** una pulizia automatica dei dati più vecchi.

### 7. Quali programmi usano i dipendenti con un proprio account?
**Chiedi:** l'elenco dei programmi e siti in cui ogni dipendente ha un account personale
(gestionale, posta, CRM, fatture, ecc.) e chi oggi chiude questi account quando qualcuno esce.
**Perché:** quando una persona esce, Argo può chiudere quegli account da solo (se il
programma lo permette) o ricordare a qualcuno di farlo, e tenerne traccia.
**Cosa cambia:** ogni programma diventa una "chiave" nel quadro accessi.

### 8. Cosa succede oggi quando qualcuno se ne va?
**Chiedi:** chi viene avvisato, chi chiude cosa, in quanto tempo. C'è mai stato un caso di
account rimasto aperto?
**Perché:** ci dice cosa deve fare Argo per prima e quanto deve essere veloce.
**Cosa cambia:** priorità tra le prossime integrazioni.

### 9. I dipendenti usano PC aziendali, personali o entrambi? E il telefono?
**Chiedi:** quanti PC aziendali, se sono gestiti da Microsoft (Intune), se qualcuno lavora
dal proprio PC o telefono.
**Perché:** la passkey si crea sul dispositivo (impronta, volto, PIN). Se un giorno l'azienda
volesse distinguere i PC aziendali da quelli personali, con Intune si può fare senza toccare
i PC a mano.
**Cosa cambia:** se e come fare la Fase 4 (dispositivi).

### 10. Serve l'accesso remoto alla rete dell'ufficio?
**Chiedi:** qualcuno lavora da fuori e deve raggiungere file o programmi che stanno in
ufficio? Oggi come fa?
**Perché:** in quel caso serve una VPN gestita da Argo (si chiude da sola all'uscita).
**Cosa cambia:** se fare la parte VPN.

### 11. Chi deve poter usare la dashboard di Argo?
**Chiedi:** solo il titolare, o anche un'altra persona (es. ufficio personale)? Chi deve
confermare se il file chiede di disattivare più persone insieme?
**Perché:** ogni persona con accesso alla dashboard ha un ruolo e vede gli stessi dati.
**Cosa cambia:** chi riceve il ruolo `iam-owner`.
