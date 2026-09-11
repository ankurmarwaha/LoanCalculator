"""Read public product reference data. Never send borrower information to banks."""
import concurrent.futures
import datetime
import json
import time
import urllib.parse
import urllib.request

BANKS = {
    'cba': ('CommBank', 'https://api.commbank.com.au/public/cds-au/v1/banking/products', 'https://www.commbank.com.au/home-loans/interest-rates.html'),
    'westpac': ('Westpac', 'https://digital-api.westpac.com.au/cds-au/v1/banking/products', 'https://www.westpac.com.au/personal-banking/home-loans/all-interest-rates/'),
}
CACHE = {}


def fetch(url, version):
    req = urllib.request.Request(url, headers={'x-v': str(version), 'Accept': 'application/json', 'User-Agent': 'Loanleaf/1.0'})
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.load(response)


def products(bank, kind):
    if bank not in BANKS or kind not in ('home', 'commercial'):
        raise ValueError('Unknown bank or loan type.')
    key = (bank, kind)
    if key in CACHE and time.time()-CACHE[key][0] < 900:
        return CACHE[key][1]
    name, base, source = BANKS[bank]
    category = 'RESIDENTIAL_MORTGAGES' if kind == 'home' else 'BUSINESS_LOANS'
    summaries = []
    page = 1
    while True:
        result = fetch(base+'?'+urllib.parse.urlencode({'product-category':category, 'effective':'CURRENT', 'page-size':100, 'page':page}), 5)
        summaries.extend(result['data']['products'])
        if page >= result.get('meta', {}).get('totalPages', 1):
            break
        page += 1
        if page > 20:
            raise ValueError('Bank catalogue exceeds supported page limit.')

    def detail(product):
        url = base+'/'+urllib.parse.quote(product['productId'], safe='')
        try:
            d = fetch(url, 6 if bank == 'cba' else 7)['data']
            rates = [r for r in d.get('lendingRates', []) if r.get('lendingRateType') in ('VARIABLE','FIXED','FLOATING') and r.get('repaymentType') in (None,'PRINCIPAL_AND_INTEREST','UNCONSTRAINED')]
            return dict(name=d.get('name', product['name']), brand=d.get('brand', name), rates=rates,
                        source=d.get('additionalInformation', {}).get('overviewUri') or source,
                        updated=d.get('lastUpdated'), constraints=d.get('constraints', []), fees=d.get('fees', []), apiSource=url)
        except Exception:
            return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        details = list(pool.map(detail, summaries))
    payload = dict(bank=name, fetchedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   products=[p for p in details if p], failed=sum(p is None for p in details), source=source)
    if payload['failed'] == 0:
        CACHE[key] = (time.time(), payload)
    return payload
