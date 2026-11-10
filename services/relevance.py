from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models import ScrapedGrant


@dataclass
class RelevanceResult:
    score: int
    level: str
    reasons: list[str]
    category: str


# Priorità Domus de Luna e varianti inglesi per le fonti europee.
CRITICAL = dict.fromkeys([
    "infanzia", "adolescenza", "tutela dei minori", "minori vulnerabili",
    "povertà educativa", "comunità educative", "comunità di accoglienza",
    "mamme con bambini", "sostegno alla genitorialità", "sostegno alle famiglie",
    "maltrattamento", "abuso", "autonomia", "inclusione sociale",
    "inserimento lavorativo", "inclusione lavorativa", "persone svantaggiate",
    "disabilità", "formazione professionale", "tirocini", "accompagnamento al lavoro",
    "impresa sociale", "cooperazione sociale", "children's rights", "child protection",
    "child poverty", "educational poverty", "childhood", "adolescence",
    "vulnerable children", "parenting support", "family support", "social inclusion",
    "labour market integration", "labor market integration", "disability",
    "vocational training", "internships", "social enterprise", "social economy",
], 12)
HIGH = dict.fromkeys([
    "disagio giovanile", "prevenzione delle dipendenze", "dispersione scolastica",
    "abbandono scolastico", "sostegno scolastico", "centri giovanili",
    "educativa di strada", "periferie", "comunità educante", "sport inclusivo",
    "laboratori artistici", "laboratori culturali", "contrasto alla povertà",
    "sostegno alimentare", "beni di prima necessità", "famiglie vulnerabili",
    "emergenza sociale", "supporto psicologico", "accompagnamento all'autonomia",
    "early school leaving", "school dropout", "youth centres", "youth centers",
    "street education", "poverty reduction", "food assistance", "vulnerable families",
    "psychological support", "independent living", "integrazione", "integration",
], 7)
MEDIUM = dict.fromkeys([
    "agricoltura sociale", "fattoria sociale", "educazione ambientale",
    "natura e inclusione", "turismo sociale", "turismo accessibile", "ristorazione sociale",
    "volontariato", "cittadinanza attiva", "educazione", "scuole", "studenti", "giovani",
    "sensibilizzazione", "campagne di informazione", "capacity building",
    "sviluppo organizzativo", "rafforzamento organizzativo", "digitalizzazione",
    "terzo settore", "ets", "fundraising", "sostenibilità economica", "innovazione sociale",
    "education", "youth", "young people", "volunteering", "non-profit", "nonprofit",
    "awareness", "empowerment", "organisational development", "adolescenti",
    "environmental education", "social farming", "accessible tourism", "social innovation",
], 4)
MEDIUM.update(dict.fromkeys([
    "formazione", "training", "migrazione", "migranti", "rifugiati", "richiedenti asilo",
    "asilo", "msna", "minori stranieri", "migration", "migrants", "refugees", "asylum",
], 2))
NEGATIVE = {
    "spettacolo dal vivo": -8, "danza": -6, "cinema": -5, "musica": -4,
    "agricoltura": -5, "patrimonio culturale": -6, "archivi": -5, "ricerca scientifica": -4,
    "sport": -4,
}

FIELD_WEIGHTS = {
    "title": 2.0,
    "objectives": 1.5,
    "activities": 1.5,
    "beneficiaries": 1.3,
    "description": 1.0,
    "eligible_entities": 0.5,
    "territory": 0.3,
    "category": 1.1,
    "tags": 1.1,
}

# Sport e cultura sono strumenti possibili, non priorità positive da soli.
# Queste regole richiedono una finalità sociale nel contenuto del progetto.
CONTEXTUAL_DOMAINS = {
    "Sport & Inclusione": (
        r"sport(?:s|iv[aoei])?|attivita (?:fisic(?:a|he)|motori[ae])|"
        r"nuoto|piscina|swimming|physical activity|outdoor|escursionismo",
        "sport / attività motorie",
        {"sport"},
    ),
    "Cultura & Inclusione": (
        r"music(?:a|ale|ali)?|attivita cultural[ei]|cultur[ae]|cultural activities|"
        r"arte|arti|arts|artistico|artistica|artistici|artistiche|teatro|theatre|theater|"
        r"danza|dance|cinema|spettacolo dal vivo|lettura|reading|bibliotec(?:a|he)|"
        r"patrimonio culturale|archivi",
        "musica / attività culturali",
        {"musica", "danza", "cinema", "spettacolo dal vivo", "patrimonio culturale", "archivi"},
    ),
}
SOCIAL_PURPOSES = {
    "inclusione e integrazione": r"inclusione(?: sociale)?|social inclusion|integrazione|integration|"
        r"coesione sociale|coesione comunitaria|social cohesion|interculturale|intercultural|dialogo interculturale",
    "persone vulnerabili e accessibilità": r"vulnerabil\w*|vulnerable|disabil\w*|disabilit\w*|"
        r"accessibilita|accessibility|migranti|migrants|rifugiat\w*|refugees|"
        r"disagio sociale|poverta educativa|educational poverty|minori a rischio|at.risk youth",
    "partecipazione e contrasto all'isolamento": r"cittadinanza attiva|active citizenship|"
        r"partecipazione (?:sociale|civica)|community participation|"
        r"isolamento sociale|social isolation|solitudine|discriminazion\w*|discrimination|"
        r"benessere (?:sociale|psicologico|della comunita)|mental well.?being|dialogo intergenerazionale|"
        r"solidarieta|solidale|solidarity|beneficenza",
}
GENERATED_CATEGORIES = {
    "Infanzia & Famiglie", "Inclusione & Lavoro", "Ambiente & Inclusione", "Povertà & Fragilità",
    "Migrazione & Accoglienza", "Soccorso & Emergenze", "Diritti & Advocacy",
    "Educazione & Giovani", "Volontariato & Terzo Settore", "Capacity building",
    "Cooperazione internazionale", "Salute & Vulnerabilità", *CONTEXTUAL_DOMAINS,
}


def norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", (text or "").replace("’", "'")).encode("ascii", "ignore").decode("ascii")
    value = value.lower().replace("–", "-")
    return re.sub(r"\s+", " ", value)


def _has(text: str, pattern: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])(?:" + pattern + r")(?![a-z0-9])", text))


def _project_windows(g: ScrapedGrant, domain: str) -> list[str]:
    # I campi strutturati descrivono lo stesso progetto. La descrizione può
    # invece contenere pagine lunghe: il contesto deve essere vicino al tema.
    windows = [norm(" ".join([g.title, g.objectives, g.activities, g.beneficiaries]))]
    description = norm(g.description)
    if _has(norm(g.title), domain):
        windows.extend(norm(g.title) + " " + sentence for sentence in
                       re.split(r"[.!?;\n]", description) if sentence.strip())
    for match in re.finditer(r"(?<![a-z0-9])(?:" + domain + r")(?![a-z0-9])", description):
        windows.append(description[max(0, match.start() - 220):match.end() + 220])
    return windows


def contextual_matches(g: ScrapedGrant) -> dict[str, str]:
    results = {}
    for category, (domain, label, _) in CONTEXTUAL_DOMAINS.items():
        for window in _project_windows(g, domain):
            if not _has(window, domain):
                continue
            purpose = next((label for label, pattern in SOCIAL_PURPOSES.items()
                            if _has(window, pattern)), None)
            # Educazione generica e formazione professionale non bastano.
            if purpose is None and _has(window, r"educazione non formale|non.formal education|"
                                        r"laboratori educativi|attivita educative") and _has(
                    window, r"bambini|minori|ragazzi|giovani|adolescenti|children|young people|youth"):
                purpose = "attività educative per bambini e giovani"
            if purpose:
                results[category] = f"{label} + {purpose}"
                break
    return results


def _match_terms(text: str, table: dict[str, int], weight: float, found: list[str]) -> float:
    score = 0.0
    for term, points in table.items():
        nterm = norm(term)
        if re.search(r"(?<![a-z0-9])" + re.escape(nterm) + r"(?![a-z0-9])", text):
            score += points * weight
            found.append(term)
    return score


def classify_category(g: ScrapedGrant, context: dict[str, str] | None = None) -> str:
    contexts = contextual_matches(g) if context is None else context
    if contexts:
        return next(iter(contexts))
    source_category = "" if g.category in GENERATED_CATEGORIES else g.category
    text = norm(" ".join([g.title, source_category, g.description, g.objectives, g.activities, " ".join(g.tags)]))
    groups = [
        ("Infanzia & Famiglie", ["infanzia", "adolescenza", "tutela dei minori", "minori vulnerabili", "comunita educative", "comunita di accoglienza", "mamme", "genitorial", "famiglie", "child", "parenting", "family support", "maltrattamento", "abuso"]),
        ("Inclusione & Lavoro", ["inserimento lavorativo", "inclusione lavorativa", "formazione professionale", "tirocini", "accompagnamento al lavoro", "impresa sociale", "cooperazione sociale", "disabil", "labour market", "labor market", "vocational", "internship", "social enterprise", "social economy"]),
        ("Ambiente & Inclusione", ["agricoltura sociale", "fattoria sociale", "educazione ambientale", "natura e inclusione", "turismo sociale", "turismo accessibile", "ristorazione sociale", "environmental education", "social farming", "accessible tourism"]),
        ("Povertà & Fragilità", ["contrasto alla poverta", "sostegno alimentare", "beni di prima necessita", "emergenza sociale", "poverty reduction", "food assistance"]),
        ("Migrazione & Accoglienza", ["migr", "rifugiat", "asilo", "msna", "stranier", "fami", "tratta", "migration", "migrants", "refugees", "asylum"]),
        ("Soccorso & Emergenze", ["search and rescue", "soccorso", "salvataggio", "annegamento", "drowning", "emergenz", "protezione civile", "rescue", "humanitarian", "sicurezza acquatica", "sicurezza in acqua", "water safety"]),
        ("Diritti & Advocacy", ["diritti umani", "diritti civili", "advocacy", "discrimin", "giustizia", "human rights"]),
        ("Educazione & Giovani", ["scuol", "educaz", "student", "giovani", "formazione", "education", "youth", "young people", "adolescenti"]),
        ("Volontariato & Terzo Settore", ["volontariat", "terzo settore", "ets", "odv", "aps"]),
        ("Capacity building", ["sviluppo organizzativo", "rafforzamento organizzativo", "capacity building", "fundraising", "digitalizz"]),
        ("Cooperazione internazionale", ["cooperazione internazionale", "cooperazione", "umanitari"]),
        ("Salute & Vulnerabilità", ["salute", "sanitari", "psicolog", "vulnerabil"]),
    ]
    for label, keys in groups:
        if any(re.search(r"\b" + re.escape(k) + (r"\b" if k in {"fami", "asilo", "tratta", "ets", "odv", "aps"} else ""), text) for k in keys):
            return label
    return g.category or "Altro"


def score_grant(g: ScrapedGrant) -> RelevanceResult:
    score = 0.0
    matched: list[str] = []
    strong_matches: set[str] = set()

    field_values = {
        "title": g.title,
        "objectives": g.objectives,
        "activities": g.activities,
        "beneficiaries": g.beneficiaries,
        "description": g.description,
        "eligible_entities": g.eligible_entities,
        "territory": g.territory,
        # Non riusare una categoria calcolata come nuova evidenza positiva.
        "category": "" if g.category in GENERATED_CATEGORIES else g.category,
        "tags": " ".join(g.tags),
    }
    for field, value in field_values.items():
        text = norm(value)
        if not text:
            continue
        weight = FIELD_WEIGHTS[field]
        local: list[str] = []
        score += _match_terms(text, CRITICAL, weight, local)
        if local:
            strong_matches.update(local)
        score += _match_terms(text, HIGH, weight, local)
        score += _match_terms(text, MEDIUM, weight, local)
        matched.extend(local)

    all_text = norm(" ".join(str(v) for v in field_values.values()))
    # Regole semantiche trasparenti: combinazioni che sono particolarmente coerenti con Domus de Luna.
    context = contextual_matches(g)
    semantic_reasons = list(context.values())
    # Un bonus per ambito, senza moltiplicarlo per sinonimi/campi ripetuti.
    score += 25 * len(context)
    combos = [
        (("poverta educativa", "scuol"), 10, "povertà educativa + scuola"),
        (("famigli", "sostegno"), 10, "famiglie + sostegno"),
        (("giovani", "lavor"), 10, "giovani + lavoro"),
        (("disabil", "inclusione"), 10, "disabilità + inclusione"),
        (("ets", "sviluppo organizzativo"), 7, "ETS + rafforzamento organizzativo"),
        (("volontariat", "formazione"), 5, "volontariato + formazione"),
    ]
    # Preferenza territoriale solo per bandi già tematicamente pertinenti.
    if score >= 12 and _has(norm(g.territory), r"sardegna|sardinia|cagliari"):
        score += 6
        semantic_reasons.append("territorio prioritario: Sardegna / Cagliari")
    for terms, bonus, reason in combos:
        if all(t in all_text for t in terms):
            score += bonus
            semantic_reasons.append(reason)

    # Penalità solo quando non c'è un segnale forte Domus de Luna.
    if not strong_matches:
        exempt = set().union(*(CONTEXTUAL_DOMAINS[key][2] for key in context))
        for term, penalty in NEGATIVE.items():
            if term not in exempt and _has(all_text, re.escape(norm(term))):
                score += penalty

    score_int = max(0, min(100, round(score)))
    # These public application channels were explicitly selected for Domus.
    # Administrative instructions alone need not repeat thematic keywords.
    if g.program == 'Richiesta diretta di contributo' and g.source_name in {
        'Fondazione Prosolidar', 'Enel Cuore', 'Intesa Sanpaolo – Fondo di Beneficenza',
        'Fondazione Charlemagne', 'Fondazione Mazzola',
    } and score_int < 12:
        score_int = 12
        semantic_reasons.append('Canale di contributo selezionato per Domus de Luna; coerenza del progetto da verificare')
    if score_int >= 50:
        level = "ALTA"
    elif score_int >= 25:
        level = "MEDIA"
    elif score_int >= 12:
        level = "BASSA"
    else:
        level = "IRRILEVANTE"

    unique_terms = []
    for t in matched:
        if t not in unique_terms:
            unique_terms.append(t)
    reasons = []
    if unique_terms:
        reasons.append("Temi rilevanti: " + ", ".join(unique_terms[:8]))
    reasons.extend(f"Regola: {x}" for x in semantic_reasons[:3])
    if not reasons:
        reasons.append("Nessun collegamento forte con le aree prioritarie di Domus de Luna")

    return RelevanceResult(score=score_int, level=level, reasons=reasons, category=classify_category(g, context))
