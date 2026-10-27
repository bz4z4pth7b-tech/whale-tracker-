"""Fetch public daily bars and SEC filing metadata; atomic snapshots preserve failures."""
import json, os, time, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from engine import validate, screen, research
from whales import collect
ROOT=Path(__file__).resolve().parents[1]
def get(url,ua='Mozilla/5.0 WhaleEdgeResearch/1.0'):
    request=urllib.request.Request(url,headers={'User-Agent':ua,'Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as r: return json.load(r)
def bars(symbol):
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=2y&interval=1d'
    r=get(url)['chart']['result'][0];q=r['indicators']['quote'][0]
    adj=r['indicators'].get('adjclose',[{}])[0].get('adjclose',q['close']); result=[]
    # Exclude the current UTC date, so incomplete daily bars never become signals.
    today=datetime.now(timezone.utc).date().isoformat()
    for i,t in enumerate(r.get('timestamp',[])):
        date=datetime.fromtimestamp(t,timezone.utc).date().isoformat()
        if date>=today or any(q[k][i] is None for k in ('open','high','low','close','volume')) or adj[i] is None: continue
        factor=adj[i]/q['close'][i]
        result.append({'date':date,**{k:q[k][i]*factor for k in ('open','high','low','close')},'volume':q['volume'][i]})
    validate(result);return result


def run():
    config=json.loads((ROOT/'research/config.json').read_text()); history={};errors=[]
    for symbol in config['symbols']:
        try:
            b=bars(symbol)
            if len(b)<22: raise ValueError('Fewer than 22 complete sessions')
            history[symbol]=b
        except Exception as e: errors.append(f'{symbol}: {type(e).__name__}: {e}')
        time.sleep(.2)
    now=datetime.now(timezone.utc).isoformat()
    report=research(history); rows=[screen(s,b) for s,b in history.items()]
    rows.sort(key=lambda x:(x['eligible'],x['relative_volume']),reverse=True)
    prior_path=ROOT/'dist/data.json'; prior=json.loads(prior_path.read_text()) if prior_path.exists() else {}
    sec=collect(config,prior); whale=sec['whales']; sec_errors=sec['errors']
    # Failed whole-source refreshes retain their old values and original timestamps.
    payload={'updated_at':now,'market_as_of':max((b[-1]['date'] for b in history.values()),default=prior.get('market_as_of')),'market_fetched_at':now if history else prior.get('market_fetched_at'),'market_status':'ok' if len(history)==len(config['symbols']) else 'partial' if history else 'unavailable','whale_fetched_at':now if sec['status']=='ok' else prior.get('whale_fetched_at'),'whale_checked_at':now,'whale_status':sec['status'],'managers':sec['managers'],'whale_events':sec['whale_events'],'purchase_coverage':sec['purchase_coverage'],'universe_count':len(config['symbols']),'screen':rows if rows else prior.get('screen',[]),'whales':whale or prior.get('whales',[]),'research':report if history else prior.get('research',report),'errors':errors+sec_errors}
    prior_path.parent.mkdir(exist_ok=True);tmp=prior_path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,indent=2,allow_nan=False));tmp.replace(prior_path)
    # Immutable date-keyed daily observations support later forward evaluation.
    archive=ROOT/'data/observations';archive.mkdir(parents=True,exist_ok=True)
    key=datetime.now(timezone.utc).date().isoformat();daily=archive/f'{key}.json'
    if history and not daily.exists(): daily.write_text(json.dumps({'recorded_at':now,'screen':rows,'selected':report.get('selected')},indent=2))
    (ROOT/'dist/managers.json').write_text(json.dumps(config['managers'],indent=2))
    print(json.dumps({'market_status':payload['market_status'],'symbols':len(history),'filings':len(whale),'errors':errors+sec_errors}))
    return payload
if __name__=='__main__':run()
