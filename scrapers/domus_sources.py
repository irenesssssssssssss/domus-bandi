"""Public funding sources selected for Domus de Luna.

Read-only listings and application instructions; never submit application forms.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

from config import ADDITIONAL_MAX_PAGES, ADDITIONAL_MAX_DETAILS
from scrapers.catalogue import CatalogueScraper, ListingItem, content_text, deadline_from_text, strict_date
from services.relevance import norm

DIRECT_PROGRAM = 'Richiesta diretta di contributo'


class ConIBambiniScraper(CatalogueScraper):
    source_name = 'Con i Bambini'
    funder = source_name
    territory = 'Italia; ambito specifico da verificare nel bando'
    listing_urls = ['https://www.conibambini.org/bandi-e-iniziative/']

    def parse_listing(self, html, url):
        # The official page embeds the select's current/expired groups as JSON.
        match = re.search(r'var\s+bandi\s*=\s*', html)
        if not match:
            raise ValueError('Elenco strutturato Con i Bambini non riconosciuto')
        data, _ = json.JSONDecoder().raw_decode(html[match.end():])
        if not isinstance(data.get('list_bandi'), list):
            raise ValueError('Gruppi bandi Con i Bambini non riconosciuti')
        items = []
        for group in data['list_bandi']:
            state = norm(group.get('text', ''))
            if state not in {'in corso', 'scaduti'}:
                self.warnings.append(f'Stato Con i Bambini da verificare: {state}')
            for entry in group.get('children', []):
                target = urljoin(url, entry.get('id', ''))
                if (urlparse(target).hostname != urlparse(url).hostname
                        or not urlparse(target).path.startswith('/bandi-e-iniziative/')
                        or not entry.get('text')):
                    raise ValueError('Scheda Con i Bambini non riconosciuta')
                items.append(ListingItem(entry['text'], target,
                    closed=True if state == 'scaduti' else None))
        return items


class ValdeseScraper(CatalogueScraper):
    source_name = 'Otto per Mille Valdese'
    funder = 'Chiesa Evangelica Valdese'
    listing_urls = ['https://www.ottopermillevaldese.org/bando-ordinario/']

    def parse_listing(self, html, url):
        items = {}
        for link in self.soup(html).select('a[href]'):
            href = urljoin(url, link['href'])
            if re.search(r'LG-01-Linee-guida-per-la-richiesta-di-finanziamento-\d{4}.*\.pdf$', href, re.I):
                year = re.search(r'finanziamento-(\d{4})', href, re.I).group(1)
                items[href] = ListingItem(f'Otto per Mille Valdese – Bando ordinario {year}', href)
        if not items:
            raise ValueError('Documento del bando ordinario Valdese non individuato')
        return list(items.values())


class DirectContributionScraper(CatalogueScraper):
    """One verified application channel, not a fabricated open call."""
    program = DIRECT_PROGRAM
    application_title = ''
    required_markers: tuple[str, ...] = ()
    content_selector = ''
    context_urls: tuple[str, ...] = ()

    def scrape(self, known_urls=None):
        url = self.listing_urls[0]
        result = self.fetch(url)
        soup = self.soup(result.text)
        section = soup.select_one(self.content_selector) if self.content_selector else None
        text = content_text(str(section) if section else result.text)
        # Some sites place the application CTA in the footer (e.g. Mazzola).
        # Validate against visible page text, while keeping navigation out of scoring.
        page_text = norm(soup.get_text(' ', strip=True))
        if not all(marker in page_text for marker in self.required_markers):
            raise ValueError('Istruzioni di richiesta contributo non riconosciute: verifica manuale necessaria')
        for context_url in self.context_urls:
            text += '\n' + content_text(self.fetch(context_url).text)
        grant = self.make_grant(ListingItem(self.application_title, result.url), text)
        # Generic instruction pages can mention deadlines for other funding lines.
        # Do not turn these into a deadline applying to the entire channel.
        grant.deadline = None
        grant.source_closed = None
        grant.requirements = ('Richiesta diretta di contributo, non bando aperto certificato. '
            'Verificare disponibilità, finestra di candidatura e requisiti sulla pagina ufficiale.')
        return [grant]


class EnelCuoreScraper(DirectContributionScraper):
    source_name = 'Enel Cuore'
    funder = source_name
    application_title = 'Enel Cuore – Proposte di progetti per il Terzo Settore'
    listing_urls = ['https://www.enelcuore.it/supporto-presentazione-progetti-terzo-settore']
    required_markers = ('presentazione', 'progetto', 'terzo settore')


class IntesaBeneficenzaScraper(DirectContributionScraper):
    source_name = 'Intesa Sanpaolo – Fondo di Beneficenza'
    funder = source_name
    application_title = 'Fondo di Beneficenza – Richieste per progetti di solidarietà e utilità sociale'
    listing_urls = ['https://group.intesasanpaolo.com/it/sociale/fondo-di-beneficenza/come-richiedere-un-contributo']
    required_markers = ('richiedere un contributo', 'senza finalita di lucro', 'richieste')
    content_selector = 'main'


class CharlemagneScraper(DirectContributionScraper):
    source_name = 'Fondazione Charlemagne'
    funder = source_name
    application_title = 'Fondazione Charlemagne – Richiesta di contributo'
    listing_urls = ['https://www.fondazionecharlemagne.org/contatti/']
    required_markers = ('richiedere', 'fondi', 'formulario')
    context_urls = ('https://www.fondazionecharlemagne.org/cosa-facciamo/progetti/',)


class MazzolaScraper(DirectContributionScraper):
    source_name = 'Fondazione Mazzola'
    funder = source_name
    application_title = 'Fondazione Mazzola – Proposte per sport inclusivo e disabilità'
    listing_urls = ['https://www.fondazionemazzola.it/selezione-progetti']
    required_markers = ('sport', 'inclusione', 'contributo')


class ProsolidarScraper(DirectContributionScraper):
    source_name = 'Fondazione Prosolidar'
    funder = source_name
    application_title = 'Fondazione Prosolidar – Richieste di finanziamento di progetti sociali'
    listing_urls = ['https://www.fondazioneprosolidar.org/index.php/progetti']
    required_markers = ('presentare', 'richieste di finanziamento')
    content_selector = '.item-page'

    def scrape(self, known_urls=None):
        grants = super().scrape(known_urls)
        # The observed page states days/months without a year. Never infer it.
        deadline = deadline_from_text(grants[0].raw_text)
        grants[0].deadline = deadline
        if deadline is None:
            self.warnings.append('Finestra di candidatura senza scadenza completa verificabile: controllare anno, apertura e chiusura sulla pagina ufficiale.')
        return grants


class RegioneSardegnaScraper(CatalogueScraper):
    source_name = 'Regione Sardegna – Bandi'
    funder = 'Regione Autonoma della Sardegna'
    territory = 'Sardegna; requisiti specifici da verificare'
    listing_urls = ['https://www.regione.sardegna.it/atti-bandi-archivi/atti-amministrativi/bandi']
    api_url = 'https://www.regione.sardegna.it/api/search?index=contentrepository'

    def read_listings(self):
        items = {}
        for page in range(ADDITIONAL_MAX_PAGES):
            body = {'from': page * 30, 'size': 30,
                'query': {'bool': {'filter': [{'term': {'tipoContenuto.keyword': 'BANDO'}}]}},
                'sort': [{'dataPubblicazione': {'order': 'desc'}}]}
            data = json.loads(self.fetch(self.api_url, method='POST', json=body).text)
            hits = data.get('hits', {}).get('hits')
            if not isinstance(hits, list) or data.get('timed_out') or data.get('_shards', {}).get('failed', 0):
                raise ValueError('Risposta ricerca Regione Sardegna incompleta/non riconosciuta')
            for hit in hits:
                row = hit.get('_source', {})
                title, slug = row.get('titolo'), row.get('slug')
                if not title or not slug or str(row.get('tipoContenuto', '')).upper() != 'BANDO':
                    raise ValueError('Record Regione Sardegna non riconosciuto')
                # Exclude procurement and staff selections; keep social funding calls.
                if re.search(r'fornitura|appalto|affidamento|concorso pubblico|selezione.*personale|procedura negoziata', title, re.I):
                    continue
                url = self.listing_urls[0] + '/' + str(slug)
                items[url] = ListingItem(title, url, content_text(row.get('oggetto') or ''),
                    deadline=strict_date(row.get('dataScadenza') or ''),
                    closed=True if norm(row.get('stato', '')) in {'chiuso', 'scaduto', 'esitato'} else None)
            total = data['hits'].get('total', 0)
            total = total.get('value', 0) if isinstance(total, dict) else total
            if len(hits) < 30 or (page + 1) * 30 >= total:
                break
        else:
            self.warnings.append(f'Archivio regionale limitato alle prime {ADDITIONAL_MAX_PAGES * 30} schede recenti.')
        return list(items.values())


class CagliariScraper(CatalogueScraper):
    source_name = 'Comune di Cagliari – Contributi e coprogettazione'
    funder = 'Comune di Cagliari'
    territory = 'Cagliari; requisiti specifici da verificare'
    listing_urls = ['https://www.comune.cagliari.it/portale/page/it/bandi_contributi',
                    'https://www.comune.cagliari.it/portale/it/doc_09_08.page']
    api_root = 'https://www.comune.cagliari.it/portale/legacyapi/rs/it/jacms/'

    @staticmethod
    def result(data):
        response = data.get('response', {})
        if response.get('errors') or not isinstance(response.get('result'), dict):
            raise ValueError('Risposta archivio comunale non riconosciuta')
        return response['result']

    def parse_card(self, data):
        result = self.result(data)
        soup = self.soup(result.get('html', ''))
        link = soup.select_one('h4 a[href]')
        if not link or urlparse(link['href']).hostname != 'www.comune.cagliari.it':
            raise ValueError('Scheda comunale senza titolo/link ufficiale')
        row = result.get('item', {})
        attributes = row.get('attributes', {}).get('attribute', [])
        attrs = {a.get('name'): a for a in attributes}
        text = '\n'.join(content_text(str(attrs.get(key, {}).get('htmlValue') or
                                          attrs.get(key, {}).get('value') or ''))
                         for key in ('titolo', 'descr', 'oggetto', 'descr_est', 'ult_info'))
        item = ListingItem(link.get_text(' ', strip=True), link['href'], text,
            deadline=strict_date(attrs.get('data_scad', {}).get('value') or ''),
            external_id=row.get('id', ''))
        return item

    def read_listings(self):
        items = {}
        self._detail_cache = {}
        for subtype in ('doc_09_05', 'doc_09_08'):
            filters = ('(attributeFilter=true;order=DESC;key=data_pubb)'
                '+(attributeFilter=true;key=tipologia;value=doc_09)'
                f'+(attributeFilter=true;key=sottotip;value={subtype})')
            data = json.loads(self.fetch(self.api_root + 'contentsExtended.json',
                params={'contentType': 'DOC', 'filters': filters}).text)
            result = self.result(data).get('items')
            if not isinstance(result, dict) or 'size' not in result:
                raise ValueError('Elenco comunale non riconosciuto')
            rows = result.get('item', [])
            rows = [rows] if isinstance(rows, dict) else rows
            limit = min(ADDITIONAL_MAX_DETAILS, ADDITIONAL_MAX_PAGES * 12)
            if int(result['size']) > limit:
                self.warnings.append(f'Archivio comunale {subtype}: lette le prime {limit} schede recenti.')
            for row in rows[:limit]:
                identifier = row.get('$', '')
                if not re.fullmatch(r'DOC\d+', identifier):
                    raise ValueError('Identificativo scheda comunale non riconosciuto')
                try:
                    card = json.loads(self.fetch(self.api_root + 'content.json',
                        params={'id': identifier, 'modelId': '700012'}).text)
                    item = self.parse_card(card)
                    items[item.url] = item
                    self._detail_cache[item.url] = item.description
                except Exception as exc:
                    self.warnings.append(f'Scheda comunale {identifier} non letta: {exc}')
        if not items and self.warnings:
            raise ValueError('Nessuna scheda comunale letta: ' + '; '.join(self.warnings))
        return list(items.values())

    def detail_text(self, item):
        cached = getattr(self, '_detail_cache', {}).get(item.url)
        return cached if cached is not None else super().detail_text(item)


DOMUS_SCRAPERS = [ConIBambiniScraper, ValdeseScraper, RegioneSardegnaScraper,
    CagliariScraper, ProsolidarScraper, EnelCuoreScraper, IntesaBeneficenzaScraper,
    CharlemagneScraper, MazzolaScraper]
