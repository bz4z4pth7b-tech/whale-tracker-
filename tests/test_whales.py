import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
from whales import parse_form4,parse_holdings,compare_holdings,feed_entries
META={'accession':'0000000001-26-000001','filed':'2026-10-27','url':'https://www.sec.gov/fixture'}
def form(code='P',amount='100001',price='2',kind='nonDerivative'):
 return f'''<ownershipDocument><documentType>4</documentType><issuer><issuerName>Fixture Inc</issuerName><issuerTradingSymbol>TEST</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerName>Test Owner</rptOwnerName><rptOwnerCik>0000001234</rptOwnerCik></reportingOwnerId></reportingOwner><{kind}Table><{kind}Transaction><securityTitle><value>Common</value></securityTitle><transactionDate><value>2026-10-25</value></transactionDate><transactionCoding><transactionCode>{code}</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>{amount}</value></transactionShares><transactionPricePerShare><value>{price}</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts><ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature></{kind}Transaction></{kind}Table></ownershipDocument>'''
def holding(extra='',unit='SH',shares='100'):
 return f'<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable"><infoTable><nameOfIssuer>Fixture</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>123456789</cusip>{extra}<shrsOrPrnAmt><sshPrnamt>{shares}</sshPrnamt><sshPrnamtType>{unit}</sshPrnamtType></shrsOrPrnAmt></infoTable></informationTable>'
class WhaleTests(unittest.TestCase):
 def test_purchase(self):
  e=parse_form4(form(),META)[0];self.assertEqual(e['shares'],100001);self.assertEqual(e['amount'],200002);self.assertEqual(e['owner_ciks'],['1234'])
 def test_awards_not_purchases(self):self.assertEqual(parse_form4(form('A'),META),[])
 def test_derivatives_not_stock_buys(self):self.assertEqual(parse_form4(form(kind='derivative'),META),[])
 def test_missing_price_stays_unknown(self):self.assertIsNone(parse_form4(form(price=''),META)[0]['amount'])
 def test_nan_rejected(self):self.assertEqual(parse_form4(form(amount='NaN'),META),[])
 def test_amendments_not_double_counted(self):self.assertEqual(parse_form4(form().replace('<documentType>4','<documentType>4/A'),META),[])
 def test_namespaces(self):self.assertEqual(parse_holdings(holding())['123456789|COM']['shares'],100)
 def test_option_underlying_shares_excluded(self):self.assertEqual(parse_holdings(holding('<putCall>CALL</putCall>')), {})
 def test_principal_amount_excluded(self):self.assertEqual(parse_holdings(holding(unit='PRN')), {})
 def test_positive_delta_is_not_purchase(self):
  meta={**META,'period':'2026-06-30','previous_period':'2026-03-31'}
  e=compare_holdings(parse_holdings(holding(shares='200')),parse_holdings(holding()),meta)[0]
  self.assertEqual(e['kind'],'reported_position_increase');self.assertEqual(e['shares_added'],100);self.assertIsNone(e['amount'])
 def test_no_comparison_across_missing_quarter(self):self.assertEqual(compare_holdings(parse_holdings(holding()),{},dict(META,period='2026-06-30',previous_period='2025-12-31')),[])
 def test_no_amended_comparison(self):self.assertEqual(compare_holdings(parse_holdings(holding()),{},dict(META,period='2026-06-30',previous_period='2026-03-31',amended=True)),[])
 def test_stable_event_id(self):self.assertEqual(parse_form4(form(),META)[0]['id'],parse_form4(form(),META)[0]['id'])
 def test_feed(self):
  text='<feed xmlns="http://www.w3.org/2005/Atom"><entry><category term="4"/><link href="https://www.sec.gov/Archives/edgar/data/1234/000000000126000001/0000000001-26-000001-index.htm"/><updated>2026-10-27T12:00:00Z</updated></entry></feed>'
  self.assertEqual(feed_entries(text)[0]['accession'],META['accession'])
if __name__=='__main__':unittest.main()
