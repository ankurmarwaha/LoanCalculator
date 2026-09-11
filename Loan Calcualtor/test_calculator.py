import unittest
from calculator import calculate, payment, schedule
from unittest.mock import patch
import banks

BASE = dict(kind='home', property=850000, deposit=170000, rate=6, years=30, extra=500, income=12000, expenses=4000, debts=500, lvrCap=80, buffer=3, dscr=1.25)


class CalculatorTests(unittest.TestCase):
    def test_known_payment(self):
        self.assertAlmostEqual(payment(100000, 6, 360), 599.550525, places=5)

    def test_zero_interest(self):
        result = calculate({**BASE, 'rate':0})
        self.assertAlmostEqual(result['monthly'], 680000/360)
        self.assertEqual(result['totalInterest'], 0)

    def test_schedule_conserves_principal(self):
        r = calculate(BASE)
        for rows in (r['base'], r['accelerated']):
            self.assertAlmostEqual(sum(v['principal'] for v in rows), r['principal'], places=5)
            self.assertEqual(rows[-1]['balance'], 0)
        self.assertEqual(len(r['base']), 360)
        self.assertGreater(r['interestSaved'], 0)
        self.assertGreater(r['monthsSaved'], 0)

    def test_no_extra(self):
        r=calculate({**BASE, 'extra':0})
        self.assertEqual(r['monthsSaved'], 0)
        self.assertEqual(r['interestSaved'], 0)

    def test_final_payment_capped(self):
        rows=schedule(100, 0, 60)
        self.assertEqual(rows[-1]['payment'], 40)

    def test_no_surplus(self):
        self.assertEqual(calculate({**BASE,'income':0})['capacity'], 0)

    def test_collateral_limit(self):
        self.assertEqual(calculate({**BASE,'income':100000})['capacity'], 680000)

    def test_commercial_coverage(self):
        a=calculate({**BASE,'kind':'commercial','income':6000,'dscr':1})
        b=calculate({**BASE,'kind':'commercial','income':6000,'dscr':1.25})
        self.assertAlmostEqual(a['serviceability']/b['serviceability'],1.25)

    def test_reject_invalid(self):
        for changes in [{'rate':float('nan')},{'property':0},{'deposit':900000},{'extra':-1},{'years':1.5},{'kind':'other'},{'income':float('inf')}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): calculate({**BASE,**changes})

    def test_huge_extra(self):
        r=calculate({**BASE,'extra':1000000})
        self.assertEqual(r['payoffMonths'],1)

    def test_bank_partial_failure_and_rate_filter(self):
        banks.CACHE.clear()
        def fake(url, version):
            if '?' in url:
                return {'data':{'products':[{'productId':'ok','name':'Loan'},{'productId':'bad','name':'Bad'}]},'meta':{'totalPages':1}}
            if url.endswith('/bad'): raise OSError()
            return {'data':{'name':'Loan','lendingRates':[{'lendingRateType':'VARIABLE','rate':'0.06'}, {'lendingRateType':'DISCOUNT','rate':'0.01'}]}}
        with patch('banks.fetch',side_effect=fake):
            data=banks.products('cba','home')
        self.assertEqual(data['failed'],1)
        self.assertEqual(len(data['products'][0]['rates']),1)
        self.assertFalse(banks.CACHE)


if __name__ == '__main__': unittest.main()
