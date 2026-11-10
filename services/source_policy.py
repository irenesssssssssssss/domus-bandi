"""Source selection for Domus de Luna; historical records remain in SQLite."""
from __future__ import annotations

import re
from collections.abc import Mapping

from services.relevance import norm


SOURCE_NOTES = {
    "Con i Bambini": "Povertà educativa minorile; verificare partenariato, territori e cofinanziamento del singolo bando.",
    "Otto per Mille Valdese": "Bando ordinario: forma giuridica, edizione, scadenza e documenti da verificare nelle linee guida ufficiali.",
    "Regione Sardegna – Bandi": "Archivio regionale misto: non tutti gli avvisi ammettono ETS o imprese sociali; lettura limitata alle schede recenti.",
    "Comune di Cagliari – Contributi e coprogettazione": "Contributi e coprogettazione: verificare soggetti ammessi, radicamento territoriale e requisiti del singolo avviso.",
    "Fondazione Prosolidar": "Richiesta diretta con finestre temporali; un giorno/mese senza anno non certifica una scadenza né un'apertura.",
    "Enel Cuore": "Richiesta diretta tramite piattaforma; verificare disponibilità e vincoli su progetti già in valutazione o realizzazione.",
    "Intesa Sanpaolo – Fondo di Beneficenza": "Richiesta diretta di liberalità: verificare regolamento, linee guida, plafond e requisiti dell'ente.",
    "Fondazione Charlemagne": "Richiesta diretta tramite formulario: verificare coerenza, disponibilità e modalità sulla pagina ufficiale.",
    "Fondazione Mazzola": "Richiesta diretta per sport inclusivo e disabilità: disponibilità e requisiti da verificare; non equivale a un bando aperto.",
    "Infobandi": "Portale per volontariato e Terzo Settore: requisiti specifici per bando.",
    "ConfiniOnline": "Portale non profit: verificare ruolo di capofila/partner e requisiti nel bando.",
    "EU Funding & Tenders": "Sono presenti opportunità per società civile/non profit; paesi, programma e consorzio da verificare.",
    "PN Inclusione": "Include avvisi per ETS e avvisi per amministrazioni/ambiti territoriali: verificare il singolo avviso.",
    "Ministero Lavoro – Terzo Settore": "Include avvisi per ODV, APS e fondazioni ETS; forma giuridica e registri da verificare.",
    "Fondazione CON IL SUD": "Opportunità per ETS nel Sud, inclusa la Sardegna; territorio, capofila e partenariato dipendono dal bando.",
    "Fondazione di Sardegna": "Ammessi anche non profit con sede fuori regione per progetti prevalentemente in Sardegna o a beneficio delle comunità sarde, secondo il bando.",
    "Fondazione Unipolis": "ACT include ETS; POP 2026 richiede enti costituiti da 2–10 anni ed entrate fino a 500.000 euro. Giovane riguarda l'ente, non i membri.",
}


def is_excluded_source(name: str) -> bool:
    return norm(name) in {
        "european youth foundation", "eyf", "csv lazio", "integrazione migranti",
        "aics", "compagnia di san paolo", "open society foundations",
    }


def is_excluded_grant(grant) -> bool:
    """Exclude EYF across sources, avoiding matches to incidental mentions in descriptions."""
    def field(key):
        return (grant.get(key, "") if isinstance(grant, Mapping) else getattr(grant, key, "")) or ""

    identity = norm(" ".join(field(key) for key in ("funder", "program", "title")))
    official = field("official_url").lower()
    return (is_excluded_source(field("source_name"))
            or bool(re.search(r"\beyf\b|european youth foundation|fondazione europea (?:per |della |dei |per la )?(?:gioventu|giovani)", identity))
            or "/european-youth-foundation/" in official)
