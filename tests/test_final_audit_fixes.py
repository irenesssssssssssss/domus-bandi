from datetime import date

import pytest

from database.repository import Repository
from models import ScrapedGrant
from services.deduplication import duplicate_score, normalize_url
from services.eligibility import evaluate_eligibility
from services.relevance import score_grant


def save(repo, g):
    r, e = score_grant(g), evaluate_eligibility(g)
    return repo.upsert_grant(g, r.score, r.level, r.reasons, r.category, e.status, e.reasons)


def test_direct_channel_stays_unverified_on_every_read_and_export(tmp_path):
    import json
    from build_public import build_public
    g = ScrapedGrant('Enel Cuore', 'https://www.enelcuore.it/example', 'channel',
        'Proposte per infanzia', funder='Enel Cuore',
        program='Richiesta diretta di contributo', eligible_entities='Enti del Terzo Settore')
    repo = Repository(tmp_path / 'channels.sqlite3')
    assert evaluate_eligibility(g).status == 'Da verificare'
    save(repo, g)
    for _ in range(2):
        row = repo.list_grants()[0]
        assert row['eligibility_status'] == 'Da verificare'
        assert any('Richiesta diretta' in reason for reason in row['eligibility_reasons'])
    output = tmp_path / 'public'
    build_public(output, repo)
    data = json.loads((output / 'data.json').read_text(encoding='utf-8'))
    assert data['items'][0]['eligibility_status'] == 'Da verificare'


@pytest.mark.parametrize('key', ['id', 'contentId', 'bando', 'download'])
def test_distinct_query_identifiers_never_merge_even_with_same_title(tmp_path, key):
    repo = Repository(tmp_path / 'ids.sqlite3')
    ids = []
    for number in (1, 2):
        g = ScrapedGrant('test', f'https://example.test/scheda?{key}={number}', str(number),
            'Infanzia e tutela dei minori', funder='Fondazione', deadline=date(2027, 1, 1),
            official_url=f'https://example.test/scheda?{key}={number}')
        ids.append(save(repo, g))
    assert ids[0] != ids[1]
    assert len(repo.list_grants(True)) == 2


def test_tracking_and_query_order_do_not_create_duplicates():
    a = 'https://www.example.test/scheda/?id=7&lang=it&utm_source=newsletter#details'
    b = 'https://example.test/scheda?lang=it&id=7&fbclid=tracking'
    assert normalize_url(a) == normalize_url(b)
    assert duplicate_score({'official_url': a}, {'official_url': b}) == 100


def test_blank_and_repeated_parameters_keep_record_identity():
    assert normalize_url('https://example.test/?id=&id=2') != normalize_url('https://example.test/?id=2')


def test_domus_registry_values_are_conservative(monkeypatch):
    from config import _registry_setting
    monkeypatch.setenv('DOMUS_RUNTS', ' YES ')
    assert _registry_setting('DOMUS_RUNTS') == 'yes'
    monkeypatch.setenv('DOMUS_RUNTS', 'not-confirmed')
    assert _registry_setting('DOMUS_RUNTS') == 'unknown'
    monkeypatch.delenv('DOMUS_RUNTS')
    monkeypatch.setenv('OPEN_ARMS_RUNTS', 'yes')
    assert _registry_setting('DOMUS_RUNTS') == 'unknown'
