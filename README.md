# Domus de Luna · Monitor Bandi

Dashboard per raccogliere opportunità di finanziamento pertinenti a Domus de Luna,
con ricerca, filtri, deduplicazione, valutazione tematica e valutazione separata
dell'ammissibilità. Usa fonti pubbliche; non invia candidature.

## Fonti attive correnti: 17

- Territorio: Regione Sardegna, Comune di Cagliari, Fondazione di Sardegna.
- Infanzia e sociale: Con i Bambini, Fondazione CON IL SUD, Otto per Mille Valdese,
  Fondazione Unipolis, PN Inclusione, Ministero Lavoro – Terzo Settore.
- Aggregatori nazionali: Infobandi e ConfiniOnline.
- Europa: EU Funding & Tenders.
- Richieste dirette: Fondazione Prosolidar, Enel Cuore, Fondo di Beneficenza
  Intesa Sanpaolo, Fondazione Charlemagne e Fondazione Mazzola.

Metodi, link ufficiali e limiti: [FONTI_DOMUS.md](FONTI_DOMUS.md).

## Avvio su Windows

Dalla cartella del progetto:

```powershell
.\Avvia-Windows.ps1
```

Lo script prepara l'ambiente e avvia il server. In alternativa:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Solo alla prima installazione, se .env non esiste:
Copy-Item .env.example .env
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

Aprire http://127.0.0.1:8000. Per caricare modifiche al codice, fermare il server
con Ctrl+C, riavviarlo e ricaricare la pagina con Ctrl+F5. Conservare `.env`,
`.venv`, `data` e `logs` durante gli aggiornamenti.

Il server controlla le fonti all'avvio e ogni 60 minuti per impostazione
predefinita. Il pulsante AGGIORNA ORA avvia un controllo in background. La pagina
legge periodicamente i dati del server; questa lettura non interroga di nuovo i siti.

## Configurazione

`.env.example` documenta i valori disponibili. Per l'ammissibilità si usano:

```env
DOMUS_RUNTS=unknown
DOMUS_ASSOCIATION_REGISTER=unknown
```

Impostare `yes` o `no` soltanto dopo aver verificato lo status dell'ente candidato.
Valori mancanti o non validi sono trattati come `unknown`. Le vecchie variabili
`OPEN_ARMS_*` non vengono riutilizzate per i requisiti di Domus.

Il database di una nuova installazione è `data/domus_bandi.sqlite3`. Se è già
presente il database storico `data/openarms_bandi.sqlite3`, viene riutilizzato
senza rinominarlo o perdere dati. `DB_PATH` permette di scegliere un percorso
esplicito. Questo nome storico non modifica il profilo tematico dell'app.

`UPDATE_INTERVAL_MINUTES`, `REFRESH_ON_STARTUP`, `REQUEST_TIMEOUT_SECONDS`,
`REQUEST_RETRIES`, `REQUEST_DELAY_SECONDS` e `REFRESH_MAX_WORKERS` regolano il
controllo delle fonti. Gli importatori rispettano i Disallow di robots.txt.
Con `ROBOTS_STRICT=true`, anche un robots.txt non verificabile blocca la lettura.

## Rilevanza e territorio

Le priorità sono infanzia, tutela dei minori, famiglie, povertà educativa,
inclusione sociale e lavorativa, disabilità e impresa sociale. Seguono giovani,
contrasto alla povertà, sostegno alimentare e psicologico. Ambiente, agricoltura
sociale, turismo accessibile e rafforzamento dell'ente sono temi mirati e trasversali.
Sono riconosciuti termini italiani e inglesi.

Sardegna e Cagliari aggiungono 6 punti ai bandi già pertinenti (almeno 12 punti),
senza escludere opportunità nazionali o europee. Sport e cultura ricevono un bonus
quando sono collegati a finalità sociali. Soccorso in mare e sicurezza acquatica
non hanno più i bonus della configurazione precedente.

Le ricerche UE includono CERV, ERASMUS, ESC e 14 termini tematici definiti in
`scrapers/eu_portal.py`. Non coprono automaticamente tutte le azioni gestite
soltanto dalle agenzie nazionali.

Soglie: ALTA da 50, MEDIA da 25, BASSA da 12, IRRILEVANTE sotto 12.
I bandi irrilevanti restano nel database. I cinque canali diretti selezionati hanno
un minimo di 12 punti con motivazione esplicita; l'ammissibilità resta Da verificare.
I punteggi vengono ricalcolati all'avvio e durante l'esportazione pubblica.

La scelta delle fonti non esclude automaticamente ogni bando destinato ad altre
regioni: gli aggregatori possono riportarlo. Il filtro Territorio e la verifica
dei requisiti del singolo avviso restano necessari.

## Scadenze, richieste dirette e ammissibilità

Tipologia e relativo filtro distinguono bandi/avvisi dalle richieste dirette.
Queste ultime conservano l'etichetta anche nel campo Programma e nelle esportazioni.
L'assenza di una scadenza non prova che una candidatura sia aperta. Date senza
anno completo non vengono completate per supposizione. I filtri sulle date
selezionano soltanto scadenze note. Lo storico scaduto è consultabile con Mostra scaduti.

L'ammissibilità è distinta dalla pertinenza: Probabilmente ammissibile,
Da verificare o Probabilmente non ammissibile. Controllare sempre soggetti ammessi,
territorio, registri, bilancio, partenariato e cofinanziamento nel documento ufficiale.
Le richieste dirette restano Da verificare anche dopo letture ed esportazioni.

## Deduplicazione

Il sistema confronta URL ufficiale, titolo, scadenza ed ente finanziatore.
Gli identificativi nei parametri URL (ad esempio id e contentId) sono conservati:
record diversi sullo stesso percorso non vengono fusi per la sola somiglianza
del titolo. Sono rimossi soltanto parametri di tracciamento noti, come utm_* e fbclid.
Le fonti di una stessa opportunità restano collegate con i rispettivi link.

La correzione impedisce nuove fusioni dovute a parametri ignorati; non separa
automaticamente eventuali fusioni storiche, che richiedono una verifica delle fonti.

## Copertura delle fonti

OK indica lettura completata, non ammissibilità o disponibilità garantita di fondi.
PARZIALE indica limiti di copertura o documenti non letti: lo stato mostra il motivo.
ERRORE indica una lettura fallita; i dati precedenti restano consultabili.

Limiti principali: `ADDITIONAL_MAX_PAGES`, `ADDITIONAL_MAX_DETAILS`,
`EU_MAX_PAGES_PER_QUERY`, `EU_PAGE_SIZE`, `INFOBANDI_MAX_PAGES` e
`CONFINIONLINE_MAX_PAGES`. Aumentarli amplia la copertura e il tempo necessario.
Ogni fonte è isolata in un importatore nella cartella `scrapers`.

## Esportazione pubblica

```powershell
python build_public.py
# Per aggiornare le fonti prima dell'esportazione:
python build_public.py --refresh
```

L'output in `public-site` contiene HTML, CSS, JavaScript, logo e dati esportati,
senza database o credenziali. Rigenerare questi file non pubblica il sito online.
Il workflow `.github/workflows/pages.yml` prevede aggiornamenti ogni ora tramite
GitHub Actions: l'automazione funziona quando repository, workflow e GitHub Pages
sono attivi. Sul sito pubblico RICARICA DATI legge l'ultima versione pubblicata.

Istruzioni aggiuntive: [PUBBLICAZIONE.md](PUBBLICAZIONE.md).

## Google Sheets opzionale

Installare `requirements-google-sheets.txt`, abilitare Google Sheets API,
condividere il foglio con il service account e configurare:

```env
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_SPREADSHEET_ID=ID_DEL_FOGLIO
GOOGLE_SHEETS_WORKSHEET=Bandi
GOOGLE_SERVICE_ACCOUNT_FILE=/percorso/service-account.json
```

Il pulsante SYNC GOOGLE SHEET è disponibile nell'app locale quando abilitato.
Il funzionamento principale non dipende da Google Sheets.

## Verifica

```powershell
python -m pytest -q
node tests/public_frontend.cjs
node --check frontend/app.js
```

I test coprono importatori, scadenze, fonti rimosse, cache, ammissibilità delle
richieste dirette, deduplicazione ed esportazioni. Il controllo JavaScript prova
il caricamento locale e pubblico senza richiedere un browser.

[VERIFICA_FONTI_DOMUS.json](VERIFICA_FONTI_DOMUS.json) riporta la verifica delle
nove nuove fonti del 10 novembre 2026. `AMMISSIBILITA_FONTI.md` e
`VERIFICA_FONTI.md` sono documenti storici del profilo precedente, non la lista
attiva. Conservare un backup del database prima di interventi manuali sui dati.
