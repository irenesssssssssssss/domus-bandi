import json
import sqlite3

import pytest

from database.repository import Repository
from models import ScrapedGrant
from services.relevance import score_grant


def grant(title="Bando progetti", **kwargs):
    return ScrapedGrant("test", "https://example.test/social", "social", title, **kwargs)


@pytest.mark.parametrize("g,category", [
    (grant("Sport per l'inclusione sociale"), "Sport & Inclusione"),
    (grant("Attività sportive", objectives="Contrastare l'isolamento sociale"), "Sport & Inclusione"),
    (grant(activities="Nuoto adattato", beneficiaries="Persone con disabilità"), "Sport & Inclusione"),
    (grant("Sport e coesione sociale"), "Sport & Inclusione"),
    (grant("Attività fisiche per la coesione sociale"), "Sport & Inclusione"),
    (grant("Musica e integrazione"), "Cultura & Inclusione"),
    (grant("Attività culturali per la coesione sociale"), "Cultura & Inclusione"),
    (grant(activities="Teatro e lettura", objectives="Contrasto alla povertà educativa"), "Cultura & Inclusione"),
    (grant("Danza accessibile", objectives="Promuovere l'accessibilità"), "Cultura & Inclusione"),
    (grant("Music for social inclusion"), "Cultura & Inclusione"),
    (grant("Biblioteche per il benessere della comunità"), "Cultura & Inclusione"),
    (grant("Musica solidale"), "Cultura & Inclusione"),
    (grant(activities="Laboratori educativi di musica", beneficiaries="Bambini e famiglie"), "Cultura & Inclusione"),
    (grant(description="Attività sportive per la partecipazione civica."), "Sport & Inclusione"),
])
def test_social_activities_receive_contextual_bonus(g, category):
    result = score_grant(g)
    assert result.score >= 25
    assert result.category == category
    assert any(reason.startswith("Regola: ") for reason in result.reasons)


@pytest.mark.parametrize("g", [
    grant("Campionato sportivo agonistico"),
    grant("Festival di musica e spettacolo dal vivo"),
    grant("Restauro del patrimonio culturale"),
    grant("Corso di formazione musicale per giovani professionisti"),
    grant("Ristrutturazione impianti sportivi", eligible_entities="ETS, associazioni per l'inclusione sociale"),

    grant(description="Finanziamenti per lo sport agonistico. " + "Regole di rendicontazione. " * 50 + "Inclusione sociale."),
    grant("Ricerca sulla gestione delle acque"),
])
def test_unrelated_activities_do_not_receive_contextual_bonus(g):
    result = score_grant(g)
    assert result.score < 25
    assert not any(reason.startswith("Regola: ") for reason in result.reasons)


@pytest.mark.parametrize("title", [
    "Corso di soccorso in acqua",
    "Formazione al salvataggio acquatico",
    "Formazione per la prevenzione dell'annegamento",
    "Formazione per la prevenzione dell’annegamento",
    "Water rescue training",
    "Drowning prevention training",
])
def test_water_rescue_training_is_no_longer_a_priority(title):
    result = score_grant(grant(title))
    assert result.level == "IRRILEVANTE"
    assert result.category == "Soccorso & Emergenze"
    assert not any("formazione / addestramento" in reason for reason in result.reasons)


def test_context_bonus_is_not_multiplied_by_synonyms_or_repeated_fields():
    short = score_grant(grant("Arte e coesione sociale"))
    repeated = score_grant(grant("Arte, musica, teatro, danza e coesione sociale",
                                activities="Arte, musica, teatro, danza e coesione sociale"))
    assert short.score == repeated.score == 25


def test_cached_grants_are_rescored_without_changing_eligibility_or_source_data(tmp_path):
    path = tmp_path / "existing.sqlite3"
    repo = Repository(path)
    g = grant("Attività culturali per la coesione sociale")
    record_id = repo.upsert_grant(g, 0, "IRRILEVANTE", [], "Altro",
                                 "Da verificare", ["Verificare territorio e requisiti"])
    with repo.conn() as c:
        before = dict(c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone())
        sources = [tuple(row) for row in c.execute("SELECT * FROM grant_sources")]
    # Simula il database di una versione senza la colonna dei tag.
    with sqlite3.connect(path) as c:
        c.execute("ALTER TABLE grants DROP COLUMN tags")
    repo = Repository(path)
    assert repo.recalculate_relevance() == 1
    assert repo.recalculate_relevance() == 0
    with repo.conn() as c:
        after = dict(c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone())
        assert sources == [tuple(row) for row in c.execute("SELECT * FROM grant_sources")]
    assert after["relevance_score"] == 25
    assert after["category"] == "Cultura & Inclusione"
    for key in before.keys() - {"category", "relevance_score", "relevance_level", "relevance_reasons", "tags"}:
        assert after[key] == before[key]


def test_rescore_preserves_tags_and_does_not_feed_categories_back_into_score(tmp_path):
    repo = Repository(tmp_path / "tags.sqlite3")
    g = grant("Attività culturali per la coesione sociale", tags=["volontariato"])
    result = score_grant(g)
    record_id = repo.upsert_grant(g, result.score, result.level, result.reasons, result.category,
                                 "Da verificare", [])
    assert repo.recalculate_relevance() == 0
    sparse = grant("Attività culturali per la coesione sociale")
    repo.upsert_grant(sparse, 25, "MEDIA", [], "Cultura & Inclusione", "Da verificare", [])
    assert repo.recalculate_relevance() == 0
    with repo.conn() as c:
        row = c.execute("SELECT * FROM grants WHERE id=?", (record_id,)).fetchone()
        assert json.loads(row["tags"]) == ["volontariato"]
        assert row["relevance_score"] == result.score

@pytest.mark.parametrize("title", [
    "Infanzia e tutela dei minori: comunità educative",
    "Sostegno alle famiglie e sostegno alla genitorialità",
    "Inserimento lavorativo e inclusione sociale per persone svantaggiate",
    "Child protection and family support for vulnerable children",
    "Social enterprise and labour market integration",
])
def test_domus_priority_projects_are_high(title):
    assert score_grant(grant(title)).level == "ALTA"


def test_sardinia_bonus_preserves_national_and_european_opportunities():
    title = "Bando per la tutela dei minori"
    national = score_grant(grant(title, territory="Italia"))
    european = score_grant(grant(title, territory="Unione europea"))
    local = score_grant(grant(title, territory="Sardegna, Cagliari"))
    assert national.score == european.score
    assert local.score == national.score + 6
    assert score_grant(grant("Bando generico", territory="Sardegna")).score == 0


def test_metadata_alone_does_not_trigger_social_activity_bonus():
    result = score_grant(grant("Festival musicale", category="Inclusione sociale", tags=["social inclusion"]))
    assert not any(reason.startswith("Regola: ") for reason in result.reasons)


@pytest.mark.parametrize("title,category", [
    ("Comunità educative per l'infanzia", "Infanzia & Famiglie"),
    ("Inserimento lavorativo", "Inclusione & Lavoro"),
    ("Fattoria sociale e agricoltura sociale", "Ambiente & Inclusione"),
    ("Contrasto alla povertà e sostegno alimentare", "Povertà & Fragilità"),
])
def test_domus_categories_are_stable_on_rescore(title, category):
    g = grant(title)
    first = score_grant(g)
    assert first.category == category
    g.category = first.category
    assert score_grant(g) == first


def test_eu_queries_follow_domus_profile():
    from scrapers.eu_portal import EuPortalScraper
    terms = EuPortalScraper.search_terms
    assert {"CERV", "ERASMUS", "ESC", "child protection", "family support", "social enterprise"} <= set(terms)
    assert not {"AMIF", "rescue", "migration"} & set(terms)