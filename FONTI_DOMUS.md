# Fonti aggiunte per Domus de Luna

Verifica HTTP delle pagine e dei servizi pubblici: 10 novembre 2026.
Il monitor comprende ora 17 fonti selezionate per Domus de Luna.
Il sito https://www.domusdeluna.it/ riporta diversi di questi enti tra i sostenitori.

## Selezione attiva

Sono rimossi CSV Lazio, Integrazione Migranti, AICS, Compagnia di San Paolo e
Open Society Foundations. Non vengono più interrogati e non compaiono tra le
fonti della dashboard. Le schede collegate esclusivamente a queste fonti sono
escluse anche dalle esportazioni; lo storico resta nel database. Una scheda
presente anche su una fonte mantenuta resta consultabile tramite quella fonte.

Restano attivi Infobandi, ConfiniOnline, EU Funding & Tenders, PN Inclusione,
Ministero Lavoro – Terzo Settore, Fondazione CON IL SUD, Fondazione di Sardegna,
Fondazione Unipolis e le nove fonti della tabella seguente.

| Fonte | Collegamento e metodo | Limite |
|---|---|---|
| Con i Bambini | https://www.conibambini.org/bandi-e-iniziative/ — JSON incorporato nella pagina ufficiale, gruppi In corso/Scaduti, schede attive | Include lo storico; nessun accesso a Chàiros. |
| Otto per Mille Valdese | https://www.ottopermillevaldese.org/bando-ordinario/ — individua e legge le linee guida PDF dell'edizione | Solo bando ordinario; l'anno dell'edizione non è una scadenza. |
| Regione Sardegna | https://www.regione.sardegna.it/atti-bandi-archivi/atti-amministrativi/bandi — API pubblica `/api/search?index=contentrepository` usata dal sito | Prime `ADDITIONAL_MAX_PAGES × 30` schede recenti; dettagli entro il limite comune. Esclude dal titolo alcuni acquisti e selezioni di personale. Non copre tutti i siti tematici FSE+/FESR. |
| Comune di Cagliari | https://www.comune.cagliari.it/portale/page/it/bandi_contributi e https://www.comune.cagliari.it/portale/it/doc_09_08.page — servizi pubblici `contentsExtended.json` e `content.json` usati dagli elenchi ufficiali | Solo contributi e coprogettazione, filtri ufficiali `doc_09_05` e `doc_09_08`. Per sezione legge al massimo il minore tra `ADDITIONAL_MAX_DETAILS` e `ADDITIONAL_MAX_PAGES × 12`. |
| Fondazione Prosolidar | https://www.fondazioneprosolidar.org/index.php/progetti — istruzioni pubbliche | Richiesta diretta con finestre. Senza anno completo, scadenza da verificare e stato PARZIALE. |
| Enel Cuore | https://www.enelcuore.it/supporto-presentazione-progetti-terzo-settore — istruzioni pubbliche | Canale di proposta diretta; nessun accesso alla piattaforma riservata. |
| Fondo di Beneficenza Intesa Sanpaolo | https://group.intesasanpaolo.com/it/sociale/fondo-di-beneficenza/come-richiedere-un-contributo — istruzioni pubbliche | Liberalità su richiesta. Le scadenze per sottolinee, ad esempio ricerca medica, non sono applicate all'intero canale. |
| Fondazione Charlemagne | https://www.fondazionecharlemagne.org/contatti/ — istruzioni del formulario e contesto dalla pagina pubblica dei progetti | Proposta diretta; nessun invio di email/moduli. Disponibilità da verificare. |
| Fondazione Mazzola | https://www.fondazionemazzola.it/selezione-progetti — criteri di selezione e richiamo pubblico alla richiesta di contributo | Proposta diretta per sport inclusivo; non importa vecchi bandi come aperti. |

## Visualizzazione e ammissibilità

Le richieste dirette hanno una colonna Tipologia e un filtro dedicato. Il campo
Programma riporta “Richiesta diretta di contributo”, anche nelle esportazioni.
Senza scadenza, la tabella mostra “Verifica finestra di richiesta”; i filtri sulle
date selezionano soltanto le scadenze note.

OK significa pagina letta, non disponibilità di fondi o apertura certificata.
Le richieste dirette mantengono l'ammissibilità Da verificare. Per ogni avviso
restano da verificare forma giuridica, territorio, partenariato e cofinanziamento.
I cinque canali diretti selezionati hanno un punteggio minimo di 12 (BASSA), con
motivazione esplicita, per restare consultabili anche quando le istruzioni non
contengono parole tematiche. Il punteggio non certifica l'ammissibilità.

Gli importatori rispettano robots.txt, ritardi e tentativi configurati nel progetto.
Una pagina non riconosciuta produce ERRORE; letture limitate o incomplete sono
PARZIALE. Nessuna candidatura viene inviata.

## Verifica e avvio

Test offline: `python -m pytest -q`.
Controllo JavaScript: `node --check frontend/app.js`.
La prima scansione reale salva dati e stati nel database locale.
Esito finale: 6 fonti OK e 3 PARZIALE, nessuna in errore. Osservati 106 record,
inclusi storico e canali di richiesta diretta: non sono 106 bandi aperti o
ammissibili. I dettagli sono in [VERIFICA_FONTI_DOMUS.json](VERIFICA_FONTI_DOMUS.json).
Riavviare il server per caricare i nuovi importatori e ricaricare la pagina per
visualizzare colonna e filtro. `python build_public.py` rigenera l'esportazione
pubblica locale senza pubblicare il sito.
