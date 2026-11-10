import json
from datetime import date
from types import SimpleNamespace

import pytest

from scrapers.domus_sources import (ConIBambiniScraper, ValdeseScraper,
    CagliariScraper, EnelCuoreScraper, ProsolidarScraper, IntesaBeneficenzaScraper,
    RegioneSardegnaScraper, DOMUS_SCRAPERS, DIRECT_PROGRAM)
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant
from services.source_policy import SOURCE_NOTES


def test_current_and_expired_bambini_calls_keep_distinct_state():
    s = ConIBambiniScraper()
    try:
        groups = [{'text': state, 'children': [{'id': s.listing_urls[0] + slug, 'text': title}]}
            for state, slug, title in [('In corso', 'new/', 'Comunità educanti'),
                                      ('Scaduti', 'old/', 'Infanzia 2024')]]
        items = s.parse_listing('<script>var bandi = ' + json.dumps({'list_bandi': groups}) + ';</script>', s.listing_urls[0])
        assert len(items) == 2
        assert items[0].closed is None and items[1].closed is True
        with pytest.raises(ValueError):
            s.parse_listing('<h1>Bandi</h1>', s.listing_urls[0])
    finally:
        s.close()


def test_valdese_uses_annual_guidelines_instead_of_results():
    s = ValdeseScraper()
    try:
        url = 'https://www.ottopermillevaldese.org/wp-content/uploads/2025/11/LG-01-Linee-guida-per-la-richiesta-di-finanziamento-2026-REV.08.pdf'
        items = s.parse_listing(f'<a href="{url}">Linee guida</a><a href="/progetti-approvati/">Esiti</a>', s.listing_urls[0])
        assert len(items) == 1 and '2026' in items[0].title
        assert items[0].deadline is None
    finally:
        s.close()


def test_direct_channel_does_not_borrow_medical_deadline(monkeypatch):
    s = IntesaBeneficenzaScraper()
    html = '<main><h1>Come richiedere un contributo</h1><p>Richieste da enti senza finalità di lucro.</p><p>Ricerca medica: domande entro il 31 maggio 2026.</p></main>'
    monkeypatch.setattr(s, 'fetch', lambda url: SimpleNamespace(url=url, text=html))
    try:
        g = s.scrape()[0]
        assert g.program == DIRECT_PROGRAM and g.deadline is None and g.source_closed is None
        assert evaluate_eligibility(g).status == 'Da verificare'
        assert score_grant(g).level == 'BASSA'
    finally:
        s.close()


def test_yearless_prosolidar_window_is_not_inferred(monkeypatch):
    s = ProsolidarScraper()
    monkeypatch.setattr(s, 'fetch', lambda url: SimpleNamespace(url=url,
        text='<div class="item-page">Sarà possibile presentare richieste di finanziamento dal 10 agosto alle 18.00 del 18 settembre.</div>'))
    try:
        assert s.scrape()[0].deadline is None
        assert score_grant(s.scrape()[0]).level == 'BASSA'
        assert any('senza scadenza completa' in w for w in s.warnings)
    finally:
        s.close()


def test_direct_channel_fails_when_page_changes(monkeypatch):
    s = EnelCuoreScraper()
    monkeypatch.setattr(s, 'fetch', lambda url: SimpleNamespace(url=url, text='<h1>Pagina non trovata</h1>'))
    try:
        with pytest.raises(ValueError):
            s.scrape()
    finally:
        s.close()


def test_application_link_in_footer_is_recognised_without_scoring_navigation(monkeypatch):
    from scrapers.domus_sources import MazzolaScraper
    s = MazzolaScraper()
    monkeypatch.setattr(s, 'fetch', lambda url: SimpleNamespace(url=url,
        text='<main>Progetti di sport inclusivo per l’inclusione.</main><footer>Richiedi un contributo</footer>'))
    try:
        g = s.scrape()[0]
        assert g.program == DIRECT_PROGRAM
        assert 'Richiedi un contributo' not in g.description
    finally:
        s.close()


def test_cagliari_uses_submission_date_not_publication():
    s = CagliariScraper()
    data = {'response': {'errors': '', 'result': {'html': '<h4><a href="https://www.comune.cagliari.it/portale/page/it/progetto?contentId=DOC123">Comunità educante</a></h4>',
        'item': {'id': 'DOC123', 'attributes': {'attribute': [
            {'name': 'data_pubb', 'value': '2026-01-01T00:00:00+01:00'},
            {'name': 'data_scad', 'value': '2026-12-15T00:00:00+01:00'},
            {'name': 'oggetto', 'value': 'Coprogettazione con Enti del Terzo Settore'},
        ]}}}}}
    try:
        item = s.parse_card(data)
        assert item.deadline == date(2026, 12, 15)
        assert item.external_id == 'DOC123'
        assert 'Terzo Settore' in item.description
        with pytest.raises(ValueError):
            s.parse_card({'response': {'errors': 'API_AUTHENTICATION_REQUIRED'}})
    finally:
        s.close()


def test_regional_paging_and_procurement_exclusion(monkeypatch):
    s = RegioneSardegnaScraper()
    rows = [{'titolo': title, 'slug': str(i), 'tipoContenuto': 'BANDO'}
            for i, title in enumerate(['Fornitura di mezzi', 'Inclusione dei bambini con disabilità'])]
    data = {'hits': {'total': {'value': 2}, 'hits': [{'_source': row} for row in rows]}}
    monkeypatch.setattr(s, 'fetch', lambda *args, **kwargs: SimpleNamespace(text=json.dumps(data)))
    try:
        items = s.read_listings()
        assert len(items) == 1 and items[0].title.startswith('Inclusione')
    finally:
        s.close()


def test_all_new_sources_have_eligibility_notes():
    assert len(DOMUS_SCRAPERS) == 9
    assert all(cls.source_name in SOURCE_NOTES for cls in DOMUS_SCRAPERS)


def test_direct_channels_remain_visible_after_cache_recalculation_and_export(tmp_path, monkeypatch):
    from database.repository import Repository
    from build_public import build_public
    repo = Repository(tmp_path / 'channels.sqlite3')
    s = ProsolidarScraper()
    monkeypatch.setattr(s, 'fetch', lambda url: SimpleNamespace(url=url,
        text='<div class="item-page">Presentare richieste di finanziamento dal 10 agosto al 18 settembre.</div>'))
    try:
        g = s.scrape()[0]
        r, e = score_grant(g), evaluate_eligibility(g)
        repo.upsert_grant(g, r.score, r.level, r.reasons, r.category, e.status, e.reasons)
        repo.upsert_grant(g, r.score, r.level, r.reasons, r.category, e.status, e.reasons)
        assert repo.recalculate_relevance() == 0
        output = tmp_path / 'public'
        build_public(output, repo)
        items = json.loads((output / 'data.json').read_text(encoding='utf-8'))['items']
        assert len(items) == 1
        assert items[0]['program'] == DIRECT_PROGRAM
        assert items[0]['relevance_level'] == 'BASSA'
        assert items[0]['eligibility_status'] == 'Da verificare'
    finally:
        s.close()
