# Guida VPS: dal primo accesso ad Argo online

Passi in ordine, da eseguire una volta sola. Le righe nei riquadri sono comandi da copiare.
`DEPLOYMENT.md` resta il riferimento tecnico; qui c'è solo il percorso pratico.

VPS: Aruba, IP `195.231.64.149`, 8 vCPU, 16 GB RAM, 160 GB.

---

## Come funziona il server (da leggere prima)

Sulla VPS gireranno circa dieci app. Ognuna ha un suo **indirizzo** (sottodominio), ma
tutti gli indirizzi portano allo stesso IP:

```
argo.azienda.it        ┐
accesso.azienda.it     ├──►  195.231.64.149
gestionale.azienda.it  ┘
```

Il browser, quando si collega, dice quale indirizzo ha digitato. All'ingresso del server
c'è un solo programma, il **proxy** (Caddy, cartella `deploy/proxy/`), che fa due cose:

1. **legge l'indirizzo e passa la richiesta all'app giusta**, come un centralino che
   smista le telefonate;
2. **fa i certificati HTTPS** (il lucchetto nel browser) per tutti gli indirizzi, da solo
   e gratis (Let's Encrypt).

Le app non sono raggiungibili direttamente da Internet: si parla solo con il proxy, e il
proxy parla con le app attraverso una "rete interna" di Docker chiamata `proxy`.

```
Internet ──► proxy (porte 80/443, HTTPS) ──rete "proxy"──┬──► Argo
                                                          ├──► gestionale
                                                          └──► ...
```

Per questo ogni app ha il suo sottodominio e non un percorso tipo `195.231.64.149/argo`:
così le app restano separate e una non può leggere i dati di accesso di un'altra.

---

## Parte 1 – Entrare nella VPS

### 1.1 Nel pannello Aruba

- **Firewall**: apri in entrata le porte **22** (SSH), **80** e **443** (siti web).
  Oggi la 22 risulta chiusa: è il motivo per cui SSH non funziona.
- **Credenziali**: annota la password di `root` (dall'email di attivazione o dal pannello).
- **Sistema operativo**: deve essere **Ubuntu Server 24.04 LTS**. Se è un altro, reinstalla
  dal pannello con Ubuntu 24.04 (la VPS è vuota, non si perde niente).

### 1.2 Dal tuo PC: prima connessione

```bash
ssh root@195.231.64.149
```

Alla domanda "Are you sure you want to continue connecting?" rispondi `yes`, poi la password.
Se va in timeout: firewall del pannello ancora chiuso (punto 1.1).

### 1.3 Accesso con chiave invece che con password

Sul **tuo PC** (non sulla VPS), se non hai già una chiave in `~/.ssh/id_ed25519`:

```bash
ssh-keygen -t ed25519            # Invio a tutte le domande va bene
ssh-copy-id root@195.231.64.149  # copia la chiave sulla VPS
ssh root@195.231.64.149          # ora entra senza password
```

### 1.4 Un utente di lavoro, non root

Sulla **VPS**, come root:

```bash
adduser argo                     # scegli una password, il resto Invio
usermod -aG sudo argo
mkdir -p /home/argo/.ssh && cp ~/.ssh/authorized_keys /home/argo/.ssh/
chown -R argo:argo /home/argo/.ssh
```

Dal tuo PC verifica che funzioni **prima** di chiudere la sessione root:

```bash
ssh argo@195.231.64.149
```

Poi spegni l'accesso con password (sulla VPS, come `argo`):

```bash
echo 'PasswordAuthentication no' | sudo tee /etc/ssh/sshd_config.d/no-password.conf
echo 'PermitRootLogin no'        | sudo tee -a /etc/ssh/sshd_config.d/no-password.conf
sudo systemctl restart ssh
```

Da qui in poi si entra sempre con `ssh argo@195.231.64.149`.

---

## Parte 2 – Preparare il server

Tutto come utente `argo`.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker argo     # poi esci e rientra (exit, ssh ...) perché valga
docker run --rm hello-world      # deve stampare "Hello from Docker!"
```

Firewall del sistema (in aggiunta a quello di Aruba):

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443
sudo ufw enable                  # conferma con y
```

---

## Parte 3 – Collegare GitHub

Il repository è **pubblico**: per scaricarlo non serve nessuna chiave.

```bash
cd ~
git clone https://github.com/mattiamare9/argo.git
```

Il codice è ora in `/home/argo/argo`. Il percorso conta: il deploy automatico (Parte 7)
entra proprio lì.

Le immagini delle app (già compilate da GitHub) si scaricano più avanti, da sole: anche
quelle sono pubbliche.

---

## Parte 4 – Prima di accendere Argo: cosa serve dal titolare

> **Non avviare Argo con valori provvisori.** Al primo avvio Keycloak (il login) salva
> dentro di sé indirizzi ed email; cambiarli dopo si può, ma solo a mano dalla sua console.

Servono:

1. **I due indirizzi** (es. `argo.azienda.it` e `accesso.azienda.it`) e qualcuno che crei
   nel DNS del dominio due record **A** verso `195.231.64.149`. Si controlla così (dal tuo PC):

   ```bash
   dig +short argo.azienda.it      # deve rispondere 195.231.64.149
   dig +short accesso.azienda.it
   ```

2. **Un modo per spedire email** (il primo amministratore riceve per email il link per
   creare la passkey). Microsoft 365 richiede l'amministratore (domanda 3 al titolare).
   In attesa va bene qualunque servizio SMTP con utente e password (anche la posta Aruba).

Le Parti 1–3 si possono fare subito; dalla Parte 5 servono queste due cose.

---

## Parte 5 – Accendere il proxy

```bash
cd ~/argo/deploy/proxy
cp .env.example .env
nano .env        # metti la tua email (avvisi di Let's Encrypt) e i due indirizzi di Argo
docker compose up -d
docker compose logs -f   # Ctrl+C per uscire
```

Finché Argo non è acceso i log mostrano errori di connessione verso `argo`: è normale.

---

## Parte 6 – Accendere Argo

### 6.1 Il file con i segreti

```bash
cd ~/argo/deploy
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Genera le password (ognuna diversa). Questo comando ne stampa una a ogni esecuzione:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32))"
```

E questo la chiave per `ARGO_SECRETS_KEY`:

```bash
python3 -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Apri `nano .env.prod` e compila:

| Voce | Cosa metterci |
|---|---|
| `ARGO_DOMAIN`, `ARGO_AUTH_DOMAIN` | i due indirizzi (gli stessi di `proxy/.env`) |
| `POSTGRES_PASSWORD`, `ARGO_APP_DB_PASSWORD`, `KEYCLOAK_DB_PASSWORD`, `KC_ADMIN_PASSWORD`, `ARGO_BACKEND_CLIENT_SECRET`, `ARGO_DASHBOARD_CLIENT_SECRET` | una password generata ciascuna |
| `ARGO_SECRETS_KEY` | la chiave generata col secondo comando |
| `ARGO_SEND_INVITES` | `false` finché non si decide il giorno di partenza (domanda 5) |
| `ARGO_SMTP_*` | i dati del servizio email |
| `ARGO_BACKUP_PASSPHRASE` | una password generata: **salvala anche fuori dalla VPS** (es. password manager), senza non si leggono i backup |

Salva una copia di `.env.prod` nel tuo password manager: se la VPS si rompe, serve quella.

### 6.2 Avvio

```bash
cd ~/argo/deploy
./deploy.sh main
```

Scarica le immagini, avvia tutto e aspetta che l'API risponda (fino a 5 minuti la prima
volta: Keycloak è lento a partire). Alla fine scrive `Deploy di main completato`.

Verifica:

```bash
docker compose -f compose.prod.yaml --env-file .env.prod ps   # tutti "running"/"healthy"
curl https://argo.azienda.it/api/health                         # "status":"ok"
```

Nel browser `https://argo.azienda.it` deve mostrare la pagina di accesso con il lucchetto.

### 6.3 Il primo amministratore

```bash
docker compose -f compose.prod.yaml --env-file .env.prod exec api \
  python -m app.cli bootstrap-admin --employee-id ADMIN --email tua@email.it \
  --first-name Nome --last-name Cognome
```

Arriva un'email "Attiva il tuo accesso ad Argo": dal link si crea la passkey.

### 6.4 La chiave per il Sync Agent

```bash
docker compose -f compose.prod.yaml --env-file .env.prod exec api \
  python -m app.cli create-agent --name excel-hr
```

La chiave compare **una volta sola**: copiala subito. Serve al programma che legge l'elenco
dei dipendenti in azienda (`sync-agent/README.md`, con `api_url = "https://argo.azienda.it"`).

---

## Parte 7 – Aggiornamenti automatici da GitHub

Dopo questa parte, ogni modifica pubblicata su `main` arriva da sola sulla VPS.
GitHub entra nella VPS con una chiave SSH sua, usata solo per questo.

Sul **tuo PC**:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/argo_deploy -N "" -C "github-deploy"
ssh-copy-id -i ~/.ssh/argo_deploy.pub argo@195.231.64.149
ssh-keyscan 195.231.64.149       # copia tutto l'output
```

Su GitHub: repository → **Settings → Secrets and variables → Actions**:

| Tipo | Nome | Valore |
|---|---|---|
| Secret | `DEPLOY_HOST` | `195.231.64.149` |
| Secret | `DEPLOY_USER` | `argo` |
| Secret | `DEPLOY_SSH_KEY` | il contenuto di `~/.ssh/argo_deploy` (il file **senza** `.pub`) |
| Secret | `DEPLOY_KNOWN_HOSTS` | l'output di `ssh-keyscan` |
| Variable | `DEPLOY_ENABLED` | `true` |

Poi cancella la chiave privata dal PC (`rm ~/.ssh/argo_deploy`): ora la conserva GitHub.

---

## Parte 8 – Backup notturno

```bash
sudo mkdir -p /var/backups/argo && sudo chown argo /var/backups/argo
crontab -e       # aggiungi la riga sotto
```

```
30 2 * * * cd /home/argo/argo/deploy && ./backup.sh compose.prod.yaml .env.prod /var/backups/argo >> /var/backups/argo/backup.log 2>&1
```

Ogni notte alle 2:30 un backup cifrato. Va anche copiato **fuori** dalla VPS (passo da
definire: uno storage esterno).

Monitoraggio: su un servizio gratuito di uptime (es. UptimeRobot) aggiungi
`https://argo.azienda.it/api/health`, controllo ogni 5 minuti, avviso via email.

---

## Aggiungere un'altra app

Esempio: un'app "gestionale" che dentro il suo container risponde sulla porta 8080, da
pubblicare su `gestionale.azienda.it`.

**1. DNS.** Record A `gestionale.azienda.it` → `195.231.64.149` (come per Argo).

**2. L'app si collega alla rete `proxy` e non apre porte.** Nel `compose.yaml` dell'app:

```yaml
services:
  gestionale:
    image: ...
    # niente "ports:" — ci pensa il proxy
    networks: [proxy]

networks:
  proxy:
    external: true   # la rete esiste già, l'ha creata il proxy
```

Se l'app ha anche un database, il database **non** va sulla rete `proxy`, solo l'app web.
Il nome del servizio (`gestionale`) deve essere unico tra tutte le app sulla rete.

**3. Dici al proxy dove mandare le richieste.** Crea il file
`~/argo/deploy/proxy/sites/gestionale.caddy` con:

```
gestionale.azienda.it {
	reverse_proxy gestionale:8080
}
```

Si legge: "chi chiede `gestionale.azienda.it`, passalo al servizio `gestionale`, porta 8080".

**4. Riavvia il proxy.**

```bash
cd ~/argo/deploy/proxy && docker compose restart caddy
```

Entro un minuto `https://gestionale.azienda.it` funziona, con il certificato già fatto.

I file in `sites/` restano solo sulla VPS (non vanno su GitHub): ogni server ha le sue app.

---

## Comandi utili

```bash
cd ~/argo/deploy
docker compose -f compose.prod.yaml --env-file .env.prod ps          # stato di Argo
docker compose -f compose.prod.yaml --env-file .env.prod logs -f api # log dell'API
cd proxy && docker compose logs -f                                    # log del proxy
docker stats                                                          # RAM e CPU per container
```
