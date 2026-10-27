import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research'))
from engine import simulate,signal,validate,research,screen

def fixture(n=220):
    from datetime import date,timedelta
    out=[]
    for i in range(n):
        p=1+i*.008
        out.append({'date':str(date(2025,1,1)+timedelta(days=i)),'open':p,'high':p+.002,'low':p-.002,'close':p,'volume':3e6 if i%8==0 else 1e6})
    return out
class EngineTests(unittest.TestCase):
    def test_signal_ignores_future(self):
        b=fixture();x=signal(b,40,'momentum');b[41]['close']=.01
        self.assertEqual(x,signal(b,40,'momentum'))
    def test_entry_is_next_session_and_exit_five_later(self):
        b=fixture();r=simulate(b,'breakout')
        self.assertTrue(r['trades'])
        for t in r['trades']:
            i=next(i for i,x in enumerate(b) if x['date']==t['signal_date'])
            self.assertEqual(t['entry_date'],b[i+1]['date']);self.assertEqual(t['exit_date'],b[i+6]['date'])
    def test_costs_reduce_return(self):
        b=fixture();self.assertLess(simulate(b,'breakout',cost_bps=150)['return'],simulate(b,'breakout',cost_bps=50)['return'])
    def test_no_exit_outside_split(self):
        b=fixture();r=simulate(b,'breakout',end=100)
        self.assertTrue(all(t['exit_date']<b[100]['date'] for t in r['trades']))
    def test_duplicates_rejected(self):
        b=fixture();b[5]['date']=b[4]['date']
        with self.assertRaises(ValueError):validate(b)
    def test_insufficient_history(self):self.assertEqual(research({'X':fixture(20)})['status'],'insufficient_history')
    def test_low_liquidity_excluded(self):
        b=fixture()
        for x in b:x['volume']=1
        self.assertFalse(screen('X',b)['eligible']);self.assertFalse(signal(b,40,'breakout'))
    def test_selection_uses_training(self):
        r=research({'X':fixture()});self.assertEqual(r['selected'],max(r['strategies'],key=lambda s:s['train_return'])['name'])
    def test_no_overlapping_positions(self):
        t=simulate(fixture(),'breakout')['trades']
        self.assertTrue(all(a['exit_date']<b['entry_date'] for a,b in zip(t,t[1:])))
    def test_cash_drawdown_and_return(self):
        b=fixture()
        for x in b:x['volume']=1
        r=simulate(b,'breakout');self.assertEqual(r['return'],0);self.assertEqual(r['drawdown'],0)
if __name__=='__main__':unittest.main()
